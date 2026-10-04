from typing import Dict, Any, Optional
from datetime import datetime, timezone
from app.services.execution_layer.executors.generic_web_executor import GenericWebExecutor
from app.services.execution_layer.models import (
    ExecutorCapabilities,
    ExecutionStatus,
    SubmissionEvidence,
)
from app.models.execution import ApplicationExecution


class LocalMockExecutor(GenericWebExecutor):
    """
    Controlled Local Mock Executor for testing and verification.
    Uses simulated HTML forms and response payloads to verify state transitions,
    anti-bot halting, field mapping, and submission confirmation logic.
    """

    source_name: str = "mock"

    SAMPLE_APPLICATION_HTML = """
    <!DOCTYPE html>
    <html>
    <head><title>Job Application - Software Engineer</title></head>
    <body>
        <h1>Apply for Software Engineer</h1>
        <form id="application-form" action="/submit" method="POST">
            <label for="full_name">Full Name *</label>
            <input type="text" id="full_name" name="full_name" required placeholder="John Doe" />

            <label for="email">Email Address *</label>
            <input type="email" id="email" name="email" required placeholder="user@example.com" />

            <label for="phone">Phone Number</label>
            <input type="tel" id="phone" name="phone" placeholder="+123456789" />

            <label for="linkedin">LinkedIn Profile</label>
            <input type="url" id="linkedin" name="linkedin" placeholder="https://linkedin.com/in/..." />

            <label for="github">GitHub Profile</label>
            <input type="url" id="github" name="github" placeholder="https://github.com/..." />

            <label for="resume">Upload Resume (PDF) *</label>
            <input type="file" id="resume" name="resume" required />

            <label for="cover_letter">Cover Letter / Note</label>
            <textarea id="cover_letter" name="cover_letter" rows="5"></textarea>

            <label for="work_authorization">Are you legally authorized to work in this country? *</label>
            <select id="work_authorization" name="work_authorization" required>
                <option value="">Select...</option>
                <option value="yes">Yes</option>
                <option value="no">No</option>
            </select>

            <label for="sponsorship">Will you require visa sponsorship? *</label>
            <select id="sponsorship" name="sponsorship" required>
                <option value="">Select...</option>
                <option value="no">No</option>
                <option value="yes">Yes</option>
            </select>

            <label for="salary_expectation">Expected Salary / CTC</label>
            <input type="text" id="salary_expectation" name="salary_expectation" placeholder="e.g. ₹3.5 LPA" />

            <button type="submit" id="submit-btn">Submit Application</button>
        </form>
    </body>
    </html>
    """

    SAMPLE_CAPTCHA_HTML = """
    <!DOCTYPE html>
    <html>
    <head><title>Security Check</title></head>
    <body>
        <h1>Security Verification Required</h1>
        <div class="g-recaptcha" data-sitekey="mock-key"></div>
        <p>Please verify you are human to continue to the application.</p>
    </body>
    </html>
    """

    SAMPLE_LOGIN_HTML = """
    <!DOCTYPE html>
    <html>
    <head><title>Sign In Required</title></head>
    <body>
        <h1>Please Sign in to apply</h1>
        <p>You must log in to apply for this job opening.</p>
        <a href="/login">Login with Google</a>
    </body>
    </html>
    """

    SAMPLE_SUCCESS_HTML = """
    <!DOCTYPE html>
    <html>
    <head><title>Application Submitted</title></head>
    <body>
        <h1>Thank you for applying!</h1>
        <p>Your application was sent successfully. We have received your application.</p>
        <p>Application ID: APP-992144-CONFIRMED</p>
    </body>
    </html>
    """
