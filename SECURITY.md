# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

We take security seriously. If you discover a security vulnerability, please follow these steps:

1. **Do not** create a public GitHub issue for security vulnerabilities
2. Email security concerns to the project maintainers
3. Include detailed information about the vulnerability
4. Wait for a response before disclosing publicly

## Security Measures

### Automated Security Scanning

- **CodeQL Analysis**: Automated code scanning for security vulnerabilities
- **Dependency Scanning**: Regular checks for vulnerable dependencies
- **Container Scanning**: Docker image vulnerability assessment

### Secure Dependencies

This project maintains security through:
- Regular dependency updates
- Use of minimal, security-focused dependencies
- Pinned dependency versions where appropriate

### Security-Critical Dependencies

The following dependencies are actively monitored for security issues:
- `setuptools>=78.1.1` (CVE-2025-47273 protection)
- `h11>=0.16.0` (CVE-2025-43859 protection)
- `requests>=2.32.0` (Security improvements)
- `urllib3>=2.2.0` (Security improvements)

## Security Best Practices

When contributing to this project:

1. **Code Review**: All changes require review before merging
2. **Principle of Least Privilege**: Minimize permissions and access
3. **Input Validation**: Validate all user inputs
4. **Secure Defaults**: Use secure configurations by default
5. **Error Handling**: Avoid exposing sensitive information in errors

## Security Contact

For security-related questions or concerns, please contact the project maintainers.