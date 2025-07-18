#!/usr/bin/env python3
"""
CalMac Website Debugging Script
This script helps us understand the current structure of the CalMac website
"""

import asyncio
import os
from playwright.async_api import async_playwright
from datetime import datetime

async def debug_calmac_website():
    """Debug the CalMac website structure"""
    print("🔍 Starting CalMac website analysis...")
    
    async with async_playwright() as p:
        # Launch browser in non-headless mode for debugging
        browser = await p.chromium.launch(
            headless=False,  # Set to True for headless mode
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu'
            ]
        )
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 720},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        page = await context.new_page()
        
        try:
            # Navigate to CalMac booking page
            print("📍 Navigating to CalMac booking page...")
            await page.goto('https://ticketing.calmac.co.uk/B2C-Calmac/#/desktop/step1/destinations/single', 
                          wait_until='domcontentloaded', timeout=45000)
            
            # Wait for page to load
            await page.wait_for_timeout(10000)
            
            # Log basic page info
            title = await page.title()
            url = page.url
            print(f"📄 Page title: {title}")
            print(f"🔗 Current URL: {url}")
            
            # Take a screenshot
            os.makedirs('debug', exist_ok=True)
            screenshot_path = f'debug/calmac_page_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png'
            await page.screenshot(path=screenshot_path, full_page=True)
            print(f"📸 Screenshot saved: {screenshot_path}")
            
            # Save page content
            content = await page.content()
            content_path = f'debug/calmac_content_{datetime.now().strftime("%Y%m%d_%H%M%S")}.html'
            with open(content_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"💾 Page content saved: {content_path}")
            
            # Analyze forms
            forms = await page.locator('form').count()
            print(f"📝 Found {forms} form elements")
            
            # Look for input fields
            inputs = await page.locator('input').count()
            selects = await page.locator('select').count()
            buttons = await page.locator('button').count()
            print(f"📝 Found {inputs} input fields, {selects} select dropdowns, {buttons} buttons")
            
            # Look for common booking elements
            booking_elements = [
                'input[name*="departure"]',
                'input[name*="arrival"]', 
                'input[name*="date"]',
                'select[name*="port"]',
                'select[name*="departure"]',
                'select[name*="arrival"]',
                'button:has-text("Search")',
                'button:has-text("Book")',
                '.booking',
                '.search',
                '.ferry'
            ]
            
            print("\n🔍 Looking for booking-related elements:")
            for selector in booking_elements:
                try:
                    count = await page.locator(selector).count()
                    if count > 0:
                        print(f"  ✅ {selector}: {count} elements found")
                    else:
                        print(f"  ❌ {selector}: not found")
                except Exception as e:
                    print(f"  ⚠️ {selector}: error - {e}")
            
            # Check for any text that mentions Troon or Brodick
            page_text = await page.inner_text('body')
            if 'Troon' in page_text:
                print("✅ Found 'Troon' in page text")
            else:
                print("❌ 'Troon' not found in page text")
                
            if 'Brodick' in page_text:
                print("✅ Found 'Brodick' in page text")
            else:
                print("❌ 'Brodick' not found in page text")
                
            # Wait a bit to see the page (if not headless)
            print("\n⏳ Waiting 30 seconds for manual inspection (if browser is visible)...")
            await page.wait_for_timeout(30000)
            
        except Exception as e:
            print(f"❌ Error during website analysis: {e}")
            # Take screenshot on error
            await page.screenshot(path=f'debug/error_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png')
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_calmac_website())
