#!/usr/bin/env python3
"""
CalMac Ferry Availability Checker
Automated script to check ferry availability and send Telegram notifications
"""

import os
import sys
import asyncio
import logging
import requests
from datetime import datetime
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

# Configure logging
def setup_logging():
    """Setup logging configuration"""
    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)
    
    # Configure logging
    log_filename = f"logs/ferry_check_{datetime.now().strftime('%Y%m%d')}.log"
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_filename),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)

def send_telegram_message(message):
    """Send a message via Telegram Bot API"""
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    
    if not bot_token or not chat_id:
        logger.error("Telegram credentials not found in environment variables")
        return False
    
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': message,
        'parse_mode': 'HTML'
    }
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        logger.info("Telegram message sent successfully")
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to send Telegram message: {e}")
        return False

async def check_ferry_availability():
    """Main function to check ferry availability using Playwright"""
    logger.info("Starting CalMac ferry availability check...")
    
    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 720},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        )
        page = await context.new_page()
        
        try:
            # Navigate to CalMac booking page
            logger.info("Navigating to CalMac booking page...")
            await page.goto('https://ticketing.calmac.co.uk/B2C-Calmac/#/desktop/step1/destinations/single', 
                          wait_until='networkidle', timeout=30000)
            
            # Wait for page to load
            await page.wait_for_timeout(3000)
            
            # Select journey type (Return should be default, but let's ensure it)
            logger.info("Selecting return journey...")
            try:
                return_radio = page.locator('input[type="radio"][value="return"], input[name="journeyType"][value="return"]')
                if await return_radio.count() > 0:
                    await return_radio.first.click()
                    await page.wait_for_timeout(1000)
            except Exception as e:
                logger.warning(f"Could not select return journey explicitly: {e}")
            
            # Select departure port (Troon)
            logger.info("Selecting departure port: Troon...")
            await page.wait_for_selector('select[name="departurePort"], #departurePort, .departure-port', timeout=10000)
            departure_select = page.locator('select[name="departurePort"], #departurePort, .departure-port').first
            await departure_select.select_option(label='Troon')
            await page.wait_for_timeout(1000)
            
            # Select arrival port (Brodick)
            logger.info("Selecting arrival port: Brodick...")
            await page.wait_for_selector('select[name="arrivalPort"], #arrivalPort, .arrival-port', timeout=10000)
            arrival_select = page.locator('select[name="arrivalPort"], #arrivalPort, .arrival-port').first
            await arrival_select.select_option(label='Brodick')
            await page.wait_for_timeout(1000)
            
            # Set outbound date (Sunday, 3 August 2025)
            logger.info("Setting outbound date: 03/08/2025...")
            outbound_date_input = page.locator('input[name="departureDate"], #departureDate, .outbound-date').first
            await outbound_date_input.fill('03/08/2025')
            await page.wait_for_timeout(1000)
            
            # Set return date (Tuesday, 5 August 2025)
            logger.info("Setting return date: 05/08/2025...")
            return_date_input = page.locator('input[name="returnDate"], #returnDate, .return-date').first
            await return_date_input.fill('05/08/2025')
            await page.wait_for_timeout(1000)
            
            # Set passengers
            logger.info("Setting passenger details...")
            
            # Adults (1)
            adult_input = page.locator('input[name="adults"], #adults, .adults-count').first
            await adult_input.fill('1')
            
            # Children (1)
            child_input = page.locator('input[name="children"], #children, .children-count').first
            await child_input.fill('1')
            
            # Infants (1)
            infant_input = page.locator('input[name="infants"], #infants, .infants-count').first
            await infant_input.fill('1')
            
            await page.wait_for_timeout(1000)
            
            # Add vehicle (Tesla Model Y / Car)
            logger.info("Adding vehicle: Car...")
            try:
                # Look for vehicle section or "Add Vehicle" button
                add_vehicle_btn = page.locator('button:has-text("Add Vehicle"), .add-vehicle, #addVehicle').first
                if await add_vehicle_btn.count() > 0:
                    await add_vehicle_btn.click()
                    await page.wait_for_timeout(1000)
                
                # Select car type
                vehicle_select = page.locator('select[name="vehicleType"], #vehicleType, .vehicle-type').first
                await vehicle_select.select_option(label='Car')
                await page.wait_for_timeout(1000)
                
                # If there are vehicle size options, select appropriate one for Tesla Model Y
                vehicle_size = page.locator('select[name="vehicleSize"], #vehicleSize, .vehicle-size')
                if await vehicle_size.count() > 0:
                    # Try to select medium/large car option
                    try:
                        await vehicle_size.select_option(label='Medium Car')
                    except:
                        try:
                            await vehicle_size.select_option(label='Large Car')
                        except:
                            logger.warning("Could not select specific vehicle size, using default")
                
            except Exception as e:
                logger.warning(f"Could not add vehicle details: {e}")
            
            # Submit the search
            logger.info("Submitting ferry search...")
            search_btn = page.locator('button:has-text("Search"), input[type="submit"], .search-button, #searchButton').first
            await search_btn.click()
            
            # Wait for results page to load
            await page.wait_for_timeout(5000)
            await page.wait_for_load_state('networkidle', timeout=30000)
            
            # Check for availability
            logger.info("Checking ferry availability...")
            
            # Look for availability indicators
            availability_found = False
            
            # Common selectors for availability
            availability_selectors = [
                '.available',
                '.booking-available', 
                'button:has-text("Book")',
                'button:has-text("Select")',
                '.ferry-available',
                '[data-available="true"]'
            ]
            
            for selector in availability_selectors:
                available_elements = page.locator(selector)
                if await available_elements.count() > 0:
                    availability_found = True
                    logger.info(f"Found availability using selector: {selector}")
                    break
            
            # Also check for "not available" or "sold out" messages
            unavailable_selectors = [
                ':has-text("Not Available")',
                ':has-text("Sold Out")',
                ':has-text("No availability")',
                '.unavailable',
                '.sold-out'
            ]
            
            unavailable_found = False
            for selector in unavailable_selectors:
                unavailable_elements = page.locator(selector)
                if await unavailable_elements.count() > 0:
                    unavailable_found = True
                    logger.info(f"Found unavailability indicator: {selector}")
                    break
            
            # Log the page content for debugging
            page_content = await page.content()
            logger.info("Page loaded successfully, checking content...")
            
            # Decision logic
            if availability_found and not unavailable_found:
                logger.info("🎉 Ferry availability FOUND!")
                
                # Send Telegram notification
                message = """🚢 CalMac Alert! Your ferry is now available:

Outbound: Troon → Brodick on Sun 03 Aug @ 07:45  
Return: Brodick → Troon on Tue 05 Aug @ 15:30  

Book now: https://ticketing.calmac.co.uk/B2C-Calmac/

Checked at: {}""".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC'))
                
                send_telegram_message(message)
                return True
                
            else:
                logger.info("❌ No ferry availability found at this time")
                return False
                
        except PlaywrightTimeoutError as e:
            logger.error(f"Timeout error during automation: {e}")
            return False
        except Exception as e:
            logger.error(f"Error during ferry availability check: {e}")
            # Take a screenshot for debugging
            try:
                await page.screenshot(path=f'logs/error_screenshot_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png')
                logger.info("Error screenshot saved")
            except:
                pass
            return False
        finally:
            await browser.close()

async def main():
    """Main entry point"""
    global logger
    logger = setup_logging()
    
    logger.info("=" * 50)
    logger.info("CalMac Ferry Availability Checker Started")
    logger.info(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    logger.info("=" * 50)
    
    try:
        availability_found = await check_ferry_availability()
        
        if availability_found:
            logger.info("✅ Check completed: Availability found and notification sent!")
            sys.exit(0)
        else:
            logger.info("ℹ️  Check completed: No availability at this time")
            sys.exit(0)
            
    except Exception as e:
        logger.error(f"Fatal error in main: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
