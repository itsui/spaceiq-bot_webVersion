"""
Login Flow Debugger
Captures complete login flow with visual highlights, screenshots, network traffic, and HTML source

Usage:
    python debug_login_flow.py

Features:
- Highlights clicked elements in red
- Captures HTML source of interacted elements
- Records all network requests/responses
- Takes screenshots at each step
- Generates detailed flow report
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright, Page, Route, Request, Response
from typing import Dict, List
import base64

class LoginFlowDebugger:
    """Captures and analyzes login flow"""

    def __init__(self):
        self.output_dir = Path('debug_login_flow') / datetime.now().strftime('%Y%m%d_%H%M%S')
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.step_counter = 0
        self.network_log = []
        self.interaction_log = []
        self.screenshots = []

        print(f"📁 Output directory: {self.output_dir}")

    async def run(self):
        """Run the interactive login flow debugger"""
        async with async_playwright() as p:
            # Launch browser in headed mode (visible)
            browser = await p.chromium.launch(
                headless=False,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--start-maximized'
                ]
            )

            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )

            page = await context.new_page()

            # Setup network monitoring
            await self._setup_network_monitoring(page)

            # Setup interaction monitoring
            await self._setup_interaction_monitoring(page)

            # Navigate to SpaceIQ login
            print("\n" + "="*70)
            print("🚀 Starting Login Flow Debugger")
            print("="*70)
            print("\n📍 Navigating to SpaceIQ login page...")

            await page.goto('https://main.spaceiq.com/login', wait_until='domcontentloaded')
            await self._capture_step(page, "Initial login page load")

            print("\n" + "="*70)
            print("👆 MANUAL INTERACTION MODE")
            print("="*70)
            print("\nPlease perform the login flow manually:")
            print("  1. Click 'Login with SSO'")
            print("  2. Enter your email")
            print("  3. Enter your password")
            print("  4. Complete MFA if required")
            print("  5. Wait until you see the SpaceIQ finder page")
            print("\n⚠️  All your clicks and typing will be captured automatically")
            print("🔴 Clicked elements will be highlighted in RED")
            print("\nPress Ctrl+C in this terminal when you're done to generate the report")
            print("="*70 + "\n")

            # Wait for user to complete login (they'll Ctrl+C when done)
            try:
                # Wait indefinitely while capturing interactions
                while True:
                    await asyncio.sleep(1)

            except KeyboardInterrupt:
                print("\n\n✅ Capturing final state...")
                await self._capture_step(page, "Final state after login")

            print("\n📊 Generating debug report...")
            await self._generate_report()

            print(f"\n✅ Debug report generated in: {self.output_dir}")
            print(f"   📄 Open: {self.output_dir / 'REPORT.html'}")

            await browser.close()

    async def _setup_network_monitoring(self, page: Page):
        """Monitor all network requests and responses"""

        async def log_request(request: Request):
            """Log outgoing request"""
            request_data = {
                'timestamp': datetime.now().isoformat(),
                'type': 'request',
                'url': request.url,
                'method': request.method,
                'headers': dict(request.headers),
                'post_data': request.post_data,
                'resource_type': request.resource_type
            }
            self.network_log.append(request_data)

            # Print important requests
            if request.method in ['POST', 'PUT'] or 'okta' in request.url or 'spaceiq' in request.url:
                print(f"   📤 {request.method} {request.url[:80]}")

        async def log_response(response: Response):
            """Log incoming response"""
            try:
                # Only capture headers and status (not body for performance)
                response_data = {
                    'timestamp': datetime.now().isoformat(),
                    'type': 'response',
                    'url': response.url,
                    'status': response.status,
                    'headers': dict(response.headers),
                    'resource_type': response.request.resource_type
                }

                # Try to capture response body for API calls
                if response.request.resource_type in ['xhr', 'fetch']:
                    try:
                        body = await response.text()
                        # Only store if not too large
                        if len(body) < 100000:  # 100KB limit
                            response_data['body'] = body
                    except:
                        response_data['body'] = '[Binary or too large]'

                self.network_log.append(response_data)

                # Print important responses
                if response.status >= 300 or 'okta' in response.url or 'spaceiq' in response.url:
                    status_emoji = "✅" if response.status < 300 else "⚠️" if response.status < 400 else "❌"
                    print(f"   📥 {status_emoji} {response.status} {response.url[:80]}")

            except Exception as e:
                print(f"   ⚠️  Error capturing response: {e}")

        page.on('request', log_request)
        page.on('response', log_response)

    async def _setup_interaction_monitoring(self, page: Page):
        """Monitor user interactions (clicks, typing)"""

        # Inject JavaScript to monitor clicks
        await page.add_init_script("""
            // Track all clicks
            document.addEventListener('click', (e) => {
                const element = e.target;

                // Highlight clicked element
                const originalBorder = element.style.border;
                const originalBackground = element.style.backgroundColor;
                element.style.border = '3px solid red';
                element.style.backgroundColor = 'rgba(255, 0, 0, 0.1)';

                // Store interaction info
                window._lastClick = {
                    timestamp: new Date().toISOString(),
                    tagName: element.tagName,
                    id: element.id,
                    className: element.className,
                    name: element.name,
                    type: element.type,
                    value: element.value,
                    text: element.textContent?.substring(0, 100),
                    outerHTML: element.outerHTML,
                    selector: getSelector(element),
                    xpath: getXPath(element)
                };

                // Keep highlight for 2 seconds
                setTimeout(() => {
                    element.style.border = originalBorder;
                    element.style.backgroundColor = originalBackground;
                }, 2000);
            }, true);

            // Track all input events
            document.addEventListener('input', (e) => {
                const element = e.target;
                window._lastInput = {
                    timestamp: new Date().toISOString(),
                    tagName: element.tagName,
                    id: element.id,
                    name: element.name,
                    type: element.type,
                    value: element.type === 'password' ? '[REDACTED]' : element.value,
                    selector: getSelector(element),
                    xpath: getXPath(element)
                };
            }, true);

            // Helper: Generate CSS selector for element
            function getSelector(element) {
                if (element.id) return '#' + element.id;
                if (element.className) {
                    const classes = element.className.split(' ').filter(c => c).join('.');
                    if (classes) return element.tagName.toLowerCase() + '.' + classes;
                }
                if (element.name) return element.tagName.toLowerCase() + '[name="' + element.name + '"]';
                return element.tagName.toLowerCase();
            }

            // Helper: Generate XPath for element
            function getXPath(element) {
                if (element.id) return '//*[@id="' + element.id + '"]';
                if (element === document.body) return '/html/body';

                let ix = 0;
                const siblings = element.parentNode?.childNodes || [];
                for (let i = 0; i < siblings.length; i++) {
                    const sibling = siblings[i];
                    if (sibling === element) {
                        return getXPath(element.parentNode) + '/' + element.tagName.toLowerCase() + '[' + (ix + 1) + ']';
                    }
                    if (sibling.nodeType === 1 && sibling.tagName === element.tagName) {
                        ix++;
                    }
                }
            }
        """)

        # Periodically check for new interactions
        async def check_interactions():
            while True:
                await asyncio.sleep(0.5)  # Check every 500ms

                try:
                    # Check for click
                    click_data = await page.evaluate("window._lastClick")
                    if click_data and click_data not in self.interaction_log:
                        self.interaction_log.append(click_data)
                        print(f"\n🖱️  CLICK detected on: {click_data['selector']}")
                        if click_data.get('text'):
                            print(f"   Text: {click_data['text'][:50]}")
                        await self._capture_step(page, f"Clicked: {click_data['selector']}", click_data)
                        # Clear it
                        await page.evaluate("window._lastClick = null")

                    # Check for input
                    input_data = await page.evaluate("window._lastInput")
                    if input_data and input_data not in self.interaction_log:
                        self.interaction_log.append(input_data)
                        print(f"\n⌨️  INPUT detected on: {input_data['selector']}")
                        print(f"   Value: {input_data['value'][:50] if len(input_data['value']) < 50 else input_data['value'][:50] + '...'}")
                        await self._capture_step(page, f"Input: {input_data['selector']}", input_data)
                        # Clear it
                        await page.evaluate("window._lastInput = null")

                except:
                    pass  # Ignore errors during monitoring

        # Start monitoring in background
        asyncio.create_task(check_interactions())

    async def _capture_step(self, page: Page, description: str, interaction_data: Dict = None):
        """Capture screenshot and page state at this step"""
        self.step_counter += 1
        step_num = f"{self.step_counter:03d}"

        print(f"   📸 Capturing step {step_num}: {description}")

        # Take screenshot
        screenshot_path = self.output_dir / f"step_{step_num}_screenshot.png"
        await page.screenshot(path=screenshot_path, full_page=False)

        # Get page HTML
        html = await page.content()
        html_path = self.output_dir / f"step_{step_num}_page.html"
        html_path.write_text(html, encoding='utf-8')

        # Get current URL
        current_url = page.url

        # Store step info
        step_data = {
            'step': self.step_counter,
            'timestamp': datetime.now().isoformat(),
            'description': description,
            'url': current_url,
            'screenshot': screenshot_path.name,
            'html_file': html_path.name,
            'interaction': interaction_data
        }

        self.screenshots.append(step_data)

        # Save step data
        step_json = self.output_dir / f"step_{step_num}_data.json"
        step_json.write_text(json.dumps(step_data, indent=2), encoding='utf-8')

    async def _generate_report(self):
        """Generate comprehensive HTML report"""

        # Save network log
        network_file = self.output_dir / 'network_log.json'
        network_file.write_text(json.dumps(self.network_log, indent=2), encoding='utf-8')

        # Save interaction log
        interaction_file = self.output_dir / 'interaction_log.json'
        interaction_file.write_text(json.dumps(self.interaction_log, indent=2), encoding='utf-8')

        # Generate HTML report
        html_report = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Login Flow Debug Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f5f5f5;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #333;
            border-bottom: 3px solid #667eea;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #667eea;
            margin-top: 30px;
        }}
        .step {{
            border: 1px solid #ddd;
            border-radius: 4px;
            padding: 20px;
            margin: 20px 0;
            background: #fafafa;
        }}
        .step-header {{
            font-size: 18px;
            font-weight: bold;
            color: #333;
            margin-bottom: 10px;
        }}
        .screenshot {{
            max-width: 100%;
            border: 2px solid #667eea;
            border-radius: 4px;
            margin: 10px 0;
        }}
        .interaction {{
            background: #fff3cd;
            padding: 10px;
            border-left: 4px solid #ffc107;
            margin: 10px 0;
            font-family: monospace;
            font-size: 12px;
        }}
        .network {{
            background: #d1ecf1;
            padding: 10px;
            border-left: 4px solid #17a2b8;
            margin: 5px 0;
            font-family: monospace;
            font-size: 11px;
        }}
        .code {{
            background: #f4f4f4;
            border: 1px solid #ddd;
            padding: 15px;
            border-radius: 4px;
            overflow-x: auto;
            font-family: 'Courier New', monospace;
            font-size: 12px;
            max-height: 400px;
            overflow-y: auto;
        }}
        .url {{
            color: #0066cc;
            word-break: break-all;
        }}
        .method {{
            font-weight: bold;
            color: #28a745;
        }}
        .method.POST {{ color: #ffc107; }}
        .method.DELETE {{ color: #dc3545; }}
        .status {{
            font-weight: bold;
        }}
        .status.success {{ color: #28a745; }}
        .status.redirect {{ color: #ffc107; }}
        .status.error {{ color: #dc3545; }}
        .summary {{
            background: #e7f3ff;
            padding: 20px;
            border-radius: 4px;
            margin: 20px 0;
        }}
        .summary-item {{
            margin: 10px 0;
            font-size: 16px;
        }}
        .label {{
            font-weight: bold;
            color: #667eea;
        }}
        pre {{
            white-space: pre-wrap;
            word-wrap: break-word;
        }}
        .tabs {{
            display: flex;
            gap: 10px;
            margin: 20px 0;
        }}
        .tab {{
            padding: 10px 20px;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
        }}
        .tab:hover {{
            background: #5568d3;
        }}
        .tab.active {{
            background: #4451b8;
        }}
        .tab-content {{
            display: none;
        }}
        .tab-content.active {{
            display: block;
        }}
    </style>
    <script>
        function showTab(tabName) {{
            // Hide all tabs
            document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.tab').forEach(el => el.classList.remove('active'));

            // Show selected tab
            document.getElementById(tabName).classList.add('active');
            document.querySelector(`[onclick="showTab('${{tabName}}')"]`).classList.add('active');
        }}
    </script>
</head>
<body>
    <div class="container">
        <h1>🔍 Login Flow Debug Report</h1>
        <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>

        <div class="summary">
            <h2>📊 Summary</h2>
            <div class="summary-item"><span class="label">Total Steps:</span> {len(self.screenshots)}</div>
            <div class="summary-item"><span class="label">Total Interactions:</span> {len(self.interaction_log)}</div>
            <div class="summary-item"><span class="label">Network Requests:</span> {len([n for n in self.network_log if n['type'] == 'request'])}</div>
            <div class="summary-item"><span class="label">Network Responses:</span> {len([n for n in self.network_log if n['type'] == 'response'])}</div>
        </div>

        <div class="tabs">
            <button class="tab active" onclick="showTab('steps')">📸 Steps & Screenshots</button>
            <button class="tab" onclick="showTab('interactions')">🖱️ Interactions</button>
            <button class="tab" onclick="showTab('network')">🌐 Network Traffic</button>
            <button class="tab" onclick="showTab('code')">💻 Code Snippets</button>
        </div>

        <div id="steps" class="tab-content active">
            <h2>📸 Login Flow Steps</h2>
            {''.join([self._generate_step_html(step) for step in self.screenshots])}
        </div>

        <div id="interactions" class="tab-content">
            <h2>🖱️ User Interactions</h2>
            {''.join([self._generate_interaction_html(interaction) for interaction in self.interaction_log])}
        </div>

        <div id="network" class="tab-content">
            <h2>🌐 Network Traffic</h2>
            <p>Total requests/responses: {len(self.network_log)}</p>
            {''.join([self._generate_network_html(net) for net in self.network_log])}
        </div>

        <div id="code" class="tab-content">
            <h2>💻 Automation Code Snippets</h2>
            <p>Based on captured interactions, here's sample Playwright code:</p>
            {self._generate_automation_code()}
        </div>
    </div>
</body>
</html>
"""

        report_path = self.output_dir / 'REPORT.html'
        report_path.write_text(html_report, encoding='utf-8')

    def _generate_step_html(self, step: Dict) -> str:
        """Generate HTML for a single step"""
        return f"""
        <div class="step">
            <div class="step-header">
                Step {step['step']}: {step['description']}
            </div>
            <p><strong>URL:</strong> <span class="url">{step['url']}</span></p>
            <p><strong>Time:</strong> {step['timestamp']}</p>
            <img src="{step['screenshot']}" class="screenshot" alt="Screenshot">
            {f'<div class="interaction"><strong>Interaction:</strong><br><pre>{json.dumps(step["interaction"], indent=2)}</pre></div>' if step.get('interaction') else ''}
            <p><a href="{step['html_file']}" target="_blank">View full page HTML →</a></p>
        </div>
        """

    def _generate_interaction_html(self, interaction: Dict) -> str:
        """Generate HTML for an interaction"""
        return f"""
        <div class="interaction">
            <strong>{interaction['timestamp']}</strong><br>
            <strong>Element:</strong> {interaction.get('tagName', 'unknown')}<br>
            <strong>Selector:</strong> <code>{interaction.get('selector', 'N/A')}</code><br>
            <strong>XPath:</strong> <code>{interaction.get('xpath', 'N/A')}</code><br>
            {f"<strong>Value:</strong> {interaction.get('value', 'N/A')}<br>" if 'value' in interaction else ''}
            {f"<strong>Text:</strong> {interaction.get('text', '')[:100]}<br>" if 'text' in interaction else ''}
            <details>
                <summary>View HTML</summary>
                <pre>{interaction.get('outerHTML', 'N/A')[:500]}</pre>
            </details>
        </div>
        """

    def _generate_network_html(self, net: Dict) -> str:
        """Generate HTML for network entry"""
        if net['type'] == 'request':
            method_class = net['method'].lower()
            return f"""
            <div class="network">
                <strong>REQUEST</strong> <span class="method {method_class}">{net['method']}</span>
                <span class="url">{net['url']}</span><br>
                <strong>Type:</strong> {net['resource_type']}<br>
                {f"<strong>POST Data:</strong> <pre>{net['post_data'][:500] if net['post_data'] else 'None'}</pre>" if net.get('post_data') else ''}
                <details>
                    <summary>Headers</summary>
                    <pre>{json.dumps(net['headers'], indent=2)}</pre>
                </details>
            </div>
            """
        else:  # response
            status_class = 'success' if net['status'] < 300 else 'redirect' if net['status'] < 400 else 'error'
            return f"""
            <div class="network">
                <strong>RESPONSE</strong> <span class="status {status_class}">{net['status']}</span>
                <span class="url">{net['url']}</span><br>
                {f"<details><summary>Body ({len(net.get('body', ''))} chars)</summary><pre>{net.get('body', 'N/A')[:1000]}</pre></details>" if net.get('body') else ''}
            </div>
            """

    def _generate_automation_code(self) -> str:
        """Generate sample Playwright automation code based on interactions"""
        code_lines = ["# Generated Playwright automation code", "async def login_to_spaceiq(page, email, password):", "    # Navigate to login"]

        for interaction in self.interaction_log:
            selector = interaction.get('selector', '')

            if 'click' in str(interaction).lower() or interaction.get('tagName') in ['BUTTON', 'A']:
                code_lines.append(f"    await page.click('{selector}')")
                code_lines.append(f"    await asyncio.sleep(1)  # Wait for page transition")

            if interaction.get('value') and interaction.get('type') != 'password':
                if 'email' in selector.lower() or interaction.get('name') == 'email':
                    code_lines.append(f"    await page.fill('{selector}', email)")
                elif 'password' in selector.lower() or interaction.get('type') == 'password':
                    code_lines.append(f"    await page.fill('{selector}', password)")
                else:
                    code_lines.append(f"    await page.fill('{selector}', 'value_here')")

        code_lines.append("")
        code_lines.append("    # Wait for navigation to complete")
        code_lines.append("    await page.wait_for_url('**/finder/**', timeout=30000)")

        code = '\n'.join(code_lines)

        return f"""
        <div class="code">
            <pre>{code}</pre>
        </div>
        <p><strong>Note:</strong> This is auto-generated based on your interactions. You may need to adjust selectors and add error handling.</p>
        """


async def main():
    debugger = LoginFlowDebugger()
    await debugger.run()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n✅ Debug session completed")
