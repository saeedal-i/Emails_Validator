# Instructions for Pushing Your Project to GitHub

## 1. Install Git

First, you need to install Git on your system:

1. Download Git from [https://git-scm.com/downloads](https://git-scm.com/downloads)
2. Run the installer and follow the installation instructions
3. After installation, open a new command prompt to ensure Git is in your PATH

## 2. Configure Git

Open a command prompt and set up your Git identity:

```
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
```

## 3. Initialize Git Repository

Navigate to your project directory and initialize a Git repository:

```
cd "D:\Emails Validator"
git init
```

## 4. Add Files to Git

Add all your project files to the Git repository:

```
git add .
```

This will add all files except those specified in the .gitignore file.

## 5. Commit Your Changes

Create your first commit:

```
git commit -m "Initial commit"
```

## 6. Create a GitHub Repository

1. Go to [GitHub](https://github.com/) and sign in (or create an account if you don't have one)
2. Click on the "+" icon in the top-right corner and select "New repository"
3. Enter a name for your repository (e.g., "email-validator")
4. Optionally add a description
5. Choose whether the repository should be public or private
6. Do NOT initialize the repository with a README, .gitignore, or license (since you're pushing an existing repository)
7. Click "Create repository"

## 7. Connect Your Local Repository to GitHub

After creating the repository, GitHub will show you commands to push an existing repository. Use the HTTPS or SSH URL provided:

### Using HTTPS (easier for beginners):

```
git remote add origin https://github.com/YOUR-USERNAME/email-validator.git
git branch -M main
git push -u origin main
```

### Using SSH (requires SSH key setup):

```
git remote add origin git@github.com:YOUR-USERNAME/email-validator.git
git branch -M main
git push -u origin main
```

Replace `YOUR-USERNAME` with your actual GitHub username and `email-validator` with your repository name if different.

## 8. Verify Your Repository

Go to `https://github.com/YOUR-USERNAME/email-validator` in your browser to see your project on GitHub.

## Additional Tips

- To update your repository after making changes:
  ```
  git add .
  git commit -m "Description of changes"
  git push
  ```

- To pull changes from GitHub to your local repository:
  ```
  git pull
  ```

- To see the status of your repository:
  ```
  git status
  ```

- To see the commit history:
  ```
  git log
  ```