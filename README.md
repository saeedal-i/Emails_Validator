# Email Validator Flask Application

This is a Python Flask application that provides a comprehensive tool to check and validate email addresses. It performs three levels of validation:

1. **Syntax Check**: RFC-compliant check for proper email format, including length limits and character validation.
2. **Domain Check**: Verifies the domain exists and has MX (Mail Exchange) records, with fallback to A records.
3. **SMTP Check**: (Mandatory when syntax and domain checks pass) Attempts to connect to the mail server to verify if the specific email address mailbox exists.

## Features

* Validate multiple email addresses at once (configurable limit)
* Comprehensive email syntax validation following RFC standards
* MX record checking with retry logic and fallback options
* SMTP verification with improved error handling and response analysis
* Detection of disposable email domains
* Simple web UI to input emails and view results
* JSON API endpoint for programmatic access
* Detailed validation results with recommendations
* Configurable via environment variables
* Extensive logging for debugging and monitoring

## Setup and Installation

1. Clone the repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Configure the application (see Configuration section)
4. Run the application:
   ```
   python app.py
   ```

## Configuration

The application can be configured using environment variables:

| Environment Variable | Description | Default Value |
|---------------------|-------------|---------------|
| SMTP_SENDER_EMAIL | Email address used for SMTP verification | verifier@yourdomain.com |
| SMTP_TIMEOUT_SECONDS | Timeout for SMTP connections | 10 |
| DNS_TIMEOUT_SECONDS | Timeout for DNS queries | 5 |
| APP_DEBUG_MODE | Enable debug mode | True |
| APP_HOST | Host to bind the server | 0.0.0.0 |
| APP_PORT | Port to bind the server | 5000 |
| MAX_EMAILS_PER_REQUEST | Maximum number of emails per request | 100 |
| ENABLE_SMTP_CHECKS | Enable SMTP verification (must be set to True) | True |

**Important**: A valid `SMTP_SENDER_EMAIL` that you control is required for the application to work properly. Without it, email validation will fail with an error message indicating that SMTP configuration is required.

## API Usage

The application provides a JSON API endpoint for email validation:

**Endpoint**: `/validate-emails`
**Method**: POST
**Content-Type**: application/json

**Request Body**:
```json
{
  "emails": ["email1@example.com", "email2@example.com"]
}
```

**Response**:
```json
{
  "results": [
    {
      "email": "email1@example.com",
      "syntax_valid": true,
      "domain_name": "example.com",
      "domain_has_mx": true,
      "mx_records": ["mx1.example.com", "mx2.example.com"],
      "smtp_check_attempted": true,
      "smtp_user_exists": true,
      "smtp_message": "Accepted by mx1.example.com (Code: 250)",
      "overall_status": "Valid (SMTP Verified)",
      "recommendation": "Email address appears to be deliverable based on SMTP check."
    },
    {
      "email": "email2@example.com",
      "syntax_valid": true,
      "domain_name": "example.com",
      "domain_has_mx": true,
      "mx_records": ["mx1.example.com", "mx2.example.com"],
      "smtp_check_attempted": true,
      "smtp_user_exists": false,
      "smtp_message": "Rejected by mx1.example.com (Code: 550, User does not exist)",
      "overall_status": "Invalid (SMTP Rejected)",
      "recommendation": "The email user likely does not exist at this domain, or mailbox is disabled."
    }
  ],
  "status": "success",
  "count": 2
}
```

## Project Structure

The application is organized as follows:

```
email-validator/
├── app.py                 # Main application file with Flask routes and email validation logic
├── requirements.txt       # Python dependencies
├── README.md              # Documentation
├── static/                # Static files
│   └── style.css          # CSS styling for the web interface
└── templates/             # HTML templates
    └── index.html         # Main HTML template for the web interface
```

### Key Components

- **app.py**: Contains the core email validation logic and Flask routes
  - `validate_email_full()`: Main function that performs all validation checks
  - `is_valid_email_syntax()`: Validates email format according to RFC standards
  - `get_mx_records()`: Checks for domain MX records with retry logic
  - `smtp_check()`: Performs SMTP verification of the mailbox
  - Flask routes for web UI and API endpoints

- **templates/index.html**: Provides a user-friendly web interface for email validation
  - Input area for multiple email addresses
  - Detailed results display
  - Copy functionality for processed results

- **static/style.css**: Styling for the web interface

## Security Considerations

- The application performs SMTP connections to mail servers, which may be rate-limited or blocked by some providers
- Ensure your `SMTP_SENDER_EMAIL` is a valid email address you control to prevent being flagged as spam
- Consider implementing rate limiting if deploying as a public service
- The application does not store email addresses or validation results

## Troubleshooting

Common issues and solutions:

1. **SMTP checks failing**: Ensure `SMTP_SENDER_EMAIL` is properly configured with a valid email address you control
2. **Timeouts during validation**: Adjust `SMTP_TIMEOUT_SECONDS` and `DNS_TIMEOUT_SECONDS` for your network conditions
3. **Rate limiting by mail servers**: If validating many emails from the same domain, spread requests over time
4. **Application not starting**: Verify all dependencies are installed with `pip install -r requirements.txt`

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
