import flask
import re
import dns.resolver
import smtplib
import socket
import logging
import traceback
import os
import io
import csv

app = flask.Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "email-tools-suite-secret-key")

class Config:
    SMTP_SENDER_EMAIL = os.environ.get('SMTP_SENDER_EMAIL', "admin@uedrop.com")
    SMTP_TIMEOUT_SECONDS = int(os.environ.get('SMTP_TIMEOUT_SECONDS', 10))
    DNS_TIMEOUT_SECONDS = int(os.environ.get('DNS_TIMEOUT_SECONDS', 5))
    APP_DEBUG_MODE = os.environ.get('APP_DEBUG_MODE', 'True').lower() in ('true', 'yes', '1', 't')
    APP_HOST = os.environ.get('APP_HOST', '0.0.0.0')
    APP_PORT = int(os.environ.get('APP_PORT', 5000))
    MAX_EMAILS_PER_REQUEST = int(os.environ.get('MAX_EMAILS_PER_REQUEST', 100))
    ENABLE_SMTP_CHECKS = os.environ.get('ENABLE_SMTP_CHECKS', 'True').lower() in ('true', 'yes', '1', 't')

app.config.from_object(Config)

if not app.debug:
    pass

try:
    socket.setdefaulttimeout(app.config['DNS_TIMEOUT_SECONDS'])
except Exception as e:
    app.logger.error(f"Failed to set default socket timeout: {e}")

# Email Validation Core Logic

def is_valid_email_syntax(email_address: str) -> bool:
    if not isinstance(email_address, str):
        return False

    email_address = email_address.strip()
    if not email_address or len(email_address) > 254:
        return False

    try:
        local_part, domain = email_address.rsplit('@', 1)
    except ValueError:
        return False

    if len(local_part) > 64 or '.' not in domain:
        return False

    regex = r'^[a-zA-Z0-9.!#$%&\'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*\.[a-zA-Z]{2,}$'
    return re.match(regex, email_address) is not None


def get_mx_records(domain: str) -> list:
    mx_hosts = []
    max_retries = 2
    retry_count = 0
    domain = domain.rstrip('.').lower()

    if not domain:
        return mx_hosts

    while retry_count <= max_retries:
        try:
            resolver = dns.resolver.Resolver()
            resolver.timeout = app.config['DNS_TIMEOUT_SECONDS']
            resolver.lifetime = app.config['DNS_TIMEOUT_SECONDS']

            mx_records_data = dns.resolver.resolve(domain, 'MX')

            mx_info = []
            for rdata in mx_records_data:
                mx_host = str(rdata.exchange).rstrip('.').lower()
                if mx_host:
                    mx_info.append({'host': mx_host, 'priority': rdata.preference})

            mx_info.sort(key=lambda x: x['priority'])
            mx_hosts = [record['host'] for record in mx_info]

            if mx_hosts:
                return mx_hosts
            else:
                break

        except dns.resolver.NXDOMAIN:
            break

        except dns.resolver.NoAnswer:
            if retry_count == max_retries:
                try:
                    a_records = dns.resolver.resolve(domain, 'A')
                    if a_records:
                        mx_hosts = [domain]
                except Exception:
                    pass

        except dns.resolver.NoNameservers:
            pass

        except dns.exception.Timeout:
            retry_count += 1
            if retry_count <= max_retries:
                continue

        except Exception as e:
            app.logger.error(f"MX Check error for {domain}: {e}")

        break

    return mx_hosts


def smtp_check(email_address: str, mx_servers: list) -> tuple[bool, str]:
    sender_email = app.config['SMTP_SENDER_EMAIL']
    smtp_timeout = app.config['SMTP_TIMEOUT_SECONDS']
    max_retries_per_server = 1

    if not isinstance(email_address, str) or not email_address.strip():
        return False, "SMTP check skipped: Invalid email address provided."

    email_address = email_address.strip().lower()

    if email_address.lower() == sender_email.lower():
        return True, "Email is the same as the sender email, so it must exist."

    if not sender_email or sender_email == "verifier@yourdomain.com":
        return False, "SMTP check skipped: SMTP_SENDER_EMAIL not properly configured."

    if not mx_servers:
        return False, "SMTP check skipped: No MX servers provided."

    try:
        local_hostname = socket.getfqdn()
    except Exception:
        local_hostname = 'localhost'

    for mx_host in mx_servers:
        retry_count = 0

        while retry_count <= max_retries_per_server:
            try:
                for port in [25]:
                    try:
                        with smtplib.SMTP(mx_host, port, timeout=smtp_timeout, local_hostname=local_hostname) as server:
                            try:
                                ehlo_resp = server.ehlo()
                                if not (200 <= ehlo_resp[0] <= 299):
                                    helo_resp = server.helo(local_hostname)
                                    if not (200 <= helo_resp[0] <= 299):
                                        raise smtplib.SMTPHeloError(helo_resp[0], "Both EHLO and HELO failed")
                            except Exception:
                                raise

                            try:
                                mail_resp = server.mail(sender_email)
                                if not (200 <= mail_resp[0] <= 299):
                                    raise smtplib.SMTPSenderRefused(mail_resp[0], mail_resp[1], sender_email)
                            except Exception:
                                raise

                            try:
                                code, message_bytes = server.rcpt(str(email_address))
                                message_str = message_bytes.decode(errors='ignore')
                            except Exception:
                                raise

                            try:
                                server.quit()
                            except Exception:
                                pass

                            if 250 <= code <= 251:
                                return True, f"Accepted by {mx_host} (Code: {code})"
                            elif code >= 500 and code <= 554:
                                message_lower = message_str.lower()
                                if any(term in message_lower for term in ["user unknown", "no such user", "does not exist", 
                                                                         "user not found", "invalid recipient", 
                                                                         "mailbox unavailable", "recipient rejected"]):
                                    return False, f"Rejected by {mx_host} (Code: {code}, User does not exist)"
                                else:
                                    return False, f"Rejected by {mx_host} (Code: {code}, User likely non-existent)"
                            elif 400 <= code <= 499:
                                pass
                            else:
                                return False, f"Inconclusive response from {mx_host} (Code: {code})"

                        break

                    except (socket.timeout, smtplib.SMTPConnectError, ConnectionRefusedError):
                        pass

            except smtplib.SMTPHeloError:
                pass
            except smtplib.SMTPRecipientsRefused as e:
                error_detail = e.recipients.get(email_address, ("Unknown SMTP Error", "Recipient Refused"))
                return False, f"Recipient refused by {mx_host} (Code: {error_detail[0]})"
            except smtplib.SMTPSenderRefused:
                return False, f"Sender email {sender_email} refused by {mx_host}."
            except (smtplib.SMTPConnectError, smtplib.SMTPServerDisconnected, socket.timeout, smtplib.SMTPException):
                pass
            except Exception as e:
                app.logger.error(f"SMTP Check error: {e}")

            retry_count += 1
            if retry_count > max_retries_per_server:
                break

    return False, "SMTP check failed for all MX servers."


def is_suspicious_local_part(local_part: str) -> tuple[bool, str]:
    if len(local_part) <= 5:
        return False, ""

    consonants = "bcdfghjklmnpqrstvwxyz"
    max_consecutive_consonants = 0
    current_consecutive = 0

    for char in local_part.lower():
        if char in consonants:
            current_consecutive += 1
            max_consecutive_consonants = max(max_consecutive_consonants, current_consecutive)
        else:
            current_consecutive = 0

    if max_consecutive_consonants >= 5:
        return True, f"Consecutive consonants"

    digit_count = sum(1 for c in local_part if c.isdigit())
    special_count = sum(1 for c in local_part if not c.isalnum())

    digit_ratio = digit_count / len(local_part)
    special_ratio = special_count / len(local_part)

    if digit_ratio > 0.5 and len(local_part) > 8:
        return True, f"High digit ratio"

    if special_ratio > 0.3:
        return True, f"High special char ratio"

    keyboard_rows = ["qwertyuiop", "asdfghjkl", "zxcvbnm"]
    for row in keyboard_rows:
        for i in range(len(row) - 3):
            pattern = row[i:i+4]
            if pattern in local_part.lower():
                return True, f"Keyboard pattern"

    unique_chars = len(set(local_part.lower()))
    entropy_ratio = unique_chars / len(local_part)

    if entropy_ratio > 0.8 and len(local_part) > 10:
        return True, f"High entropy"

    return False, ""


def validate_email_full(email_address: str) -> dict:
    result = {
        "email": email_address,
        "syntax_valid": False,
        "domain_name": None,
        "domain_has_mx": False,
        "mx_records": [],
        "smtp_check_attempted": False,
        "smtp_user_exists": False,
        "smtp_message": "Not Performed",
        "overall_status": "Unknown",
        "recommendation": ""
    }

    if not isinstance(email_address, str) or not email_address.strip():
        result["overall_status"] = "Invalid Input"
        result["recommendation"] = "Email address is empty or not a valid string."
        return result

    email_address = email_address.strip()
    result["email"] = email_address

    result["syntax_valid"] = is_valid_email_syntax(email_address)
    if not result["syntax_valid"]:
        result["overall_status"] = "Invalid Syntax"
        result["recommendation"] = "Email format is incorrect."
        return result

    try:
        local_part, domain_name = email_address.rsplit('@', 1)
        result["domain_name"] = domain_name.lower()

        is_suspicious, reason = is_suspicious_local_part(local_part)
        if is_suspicious:
            result["is_suspicious_local_part"] = True
            result["suspicious_reason"] = reason
        else:
            result["is_suspicious_local_part"] = False
    except ValueError:
        result["overall_status"] = "Invalid Syntax"
        result["recommendation"] = "Email format is malformed."
        return result

    disposable_domains = [
        "mailinator.com", "tempmail.com", "throwawaymail.com", "guerrillamail.com", 
        "10minutemail.com", "yopmail.com", "tempinbox.com", "sharklasers.com"
    ]
    if domain_name.lower() in disposable_domains:
        result["is_disposable"] = True

    mx_hosts = get_mx_records(domain_name)
    if mx_hosts:
        result["domain_has_mx"] = True
        result["mx_records"] = mx_hosts
    else:
        result["overall_status"] = "Domain/MX Issue"
        result["smtp_message"] = "No MX records found or domain does not exist."
        result["recommendation"] = "The domain may not exist or not configured for email."
        return result

    if not app.config.get('ENABLE_SMTP_CHECKS', True):
        result["overall_status"] = "Error: SMTP Checks Required"
        result["smtp_message"] = "SMTP checks are disabled globally."
        result["recommendation"] = "Enable SMTP checks in configuration."
        return result

    sender_email = app.config['SMTP_SENDER_EMAIL']

    if email_address.lower() == sender_email.lower():
        result["smtp_check_attempted"] = True
        result["smtp_user_exists"] = True
        result["smtp_message"] = "Email is the same as the sender email."
        result["overall_status"] = "Valid (Self-Verification)"
        result["recommendation"] = "Email is valid (sender email)."
        return result

    if not sender_email or sender_email == "verifier@yourdomain.com":
        result["overall_status"] = "Error: SMTP Configuration Required"
        result["smtp_message"] = "SMTP_SENDER_EMAIL not properly configured."
        result["recommendation"] = "Configure a valid SMTP_SENDER_EMAIL."
        return result

    result["smtp_check_attempted"] = True
    smtp_exists, smtp_msg = smtp_check(email_address, mx_hosts)
    result["smtp_user_exists"] = smtp_exists
    result["smtp_message"] = smtp_msg

    if smtp_exists:
        result["overall_status"] = "Valid (SMTP Verified)"
        result["recommendation"] = "Email address appears to be deliverable."
    else:
        smtp_msg_lower = smtp_msg.lower()
        rejection_indicators = [
            "rejected", "non-existent", "refused", "no such user", "does not exist", 
            "user not found", "invalid recipient", "mailbox unavailable", "recipient rejected"
        ]

        if any(indicator in smtp_msg_lower for indicator in rejection_indicators):
            result["overall_status"] = "Invalid (SMTP Rejected)"
            result["recommendation"] = "The email user likely does not exist."
        elif "skipped" in smtp_msg_lower:
            result["overall_status"] = "Error: SMTP Check Failed"
            result["recommendation"] = f"SMTP check was skipped: {smtp_msg}."
        else:
            result["overall_status"] = "Potentially Valid"
            result["recommendation"] = "Could not definitively verify user via SMTP."

    return result


# --- Flask Routes ---

@app.route('/')
def route_index():
    try:
        return flask.render_template('index.html')
    except Exception as e:
        app.logger.error(f"Error rendering index.html: {e}")
        return "Error: Could not load the page.", 500


@app.route('/validator/validate-emails', methods=['POST'])
def route_validate_emails():
    client_ip = flask.request.remote_addr

    if not flask.request.is_json:
        return flask.jsonify({
            "error": "Invalid request: Content-Type must be application/json.",
            "status": "error"
        }), 415

    try:
        try:
            data = flask.request.get_json()
        except Exception:
            return flask.jsonify({
                "error": "Invalid JSON format.",
                "status": "error"
            }), 400

        if not data or not isinstance(data, dict):
            return flask.jsonify({
                "error": "Invalid input payload. Expected JSON object.",
                "status": "error"
            }), 400

        if 'emails' not in data:
            return flask.jsonify({
                "error": "Missing 'emails' field.",
                "status": "error"
            }), 400

        if not isinstance(data['emails'], list):
            return flask.jsonify({
                "error": "'emails' field must be a list.",
                "status": "error"
            }), 400

        emails_to_validate = data['emails']

        if not emails_to_validate:
            return flask.jsonify({
                "results": [],
                "status": "success",
                "message": "No emails to validate"
            })

        max_emails = app.config['MAX_EMAILS_PER_REQUEST']
        if len(emails_to_validate) > max_emails:
            return flask.jsonify({
                "error": f"Too many emails. Maximum allowed is {max_emails}.",
                "status": "error"
            }), 413

        validation_results = []
        for email_str in emails_to_validate:
            if isinstance(email_str, str):
                try:
                    validation_results.append(validate_email_full(email_str))
                except Exception as e:
                    app.logger.error(f"Error validating '{email_str}': {e}")
                    validation_results.append({
                        "email": email_str, 
                        "syntax_valid": False, 
                        "domain_name": None, 
                        "domain_has_mx": False,
                        "mx_records": [], 
                        "smtp_check_attempted": False, 
                        "smtp_user_exists": False,
                        "smtp_message": "Internal validation error", 
                        "overall_status": "Error During Validation",
                        "recommendation": "Server-side error during validation."
                    })
            else:
                validation_results.append({
                    "email": str(email_str), 
                    "syntax_valid": False, 
                    "domain_name": None, 
                    "domain_has_mx": False,
                    "mx_records": [], 
                    "smtp_check_attempted": False, 
                    "smtp_user_exists": False,
                    "smtp_message": "Invalid input type.",
                    "overall_status": "Invalid Input Type",
                    "recommendation": "Provide a valid string."
                })

        return flask.jsonify({
            "results": validation_results,
            "status": "success",
            "count": len(validation_results)
        }), 200

    except Exception as e:
        app.logger.error(f"Error in /validate-emails: {e}")
        return flask.jsonify({
            "error": "Internal server error.",
            "status": "error"
        }), 500




if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG if app.config['APP_DEBUG_MODE'] else logging.INFO,
                        format='%(asctime)s %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s')

    app.logger.info("Starting Email Tools Suite Application")
    app.logger.info("Integrated Email Validator and Email Extractor functionalities")

    if app.config['SMTP_SENDER_EMAIL'] == "admin@uedrop.com":
        app.logger.warning("Default SMTP_SENDER_EMAIL in use. Change to a real email for better results.")

    app.run(host=app.config['APP_HOST'],
            port=app.config['APP_PORT'],
            debug=app.config['APP_DEBUG_MODE'])
