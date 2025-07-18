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
    
    # Get logger instance
    logger = logging.getLogger(__name__)
    
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
    logger = logging.getLogger(__name__)
    logger.info("Starting CalMac ferry availability check...")
    
    async with async_playwright() as p:
        # Launch browser with additional options for stability
        browser = await p.chromium.launch(
            headless=True,
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
            logger.info("Navigating to CalMac booking page...")
            await page.goto('https://ticketing.calmac.co.uk/B2C-Calmac/#/desktop/step1/destinations/single', 
                          wait_until='domcontentloaded', timeout=45000)
            
            # Wait for page to load completely
            await page.wait_for_timeout(5000)
            
            # Wait for the main form to be visible
            await page.wait_for_selector('form, .booking-form, .search-form', timeout=15000)
            
            # Select journey type (Return should be default, but let's ensure it)
            logger.info("Selecting return journey...")
            try:
                # Try multiple selectors for return journey
                return_selectors = [
                    'input[type="radio"][value="return"]',
                    'input[name="journeyType"][value="return"]',
                    '.return-journey input',
                    'label:has-text("Return") input'
                ]
                
                for selector in return_selectors:
                    return_radio = page.locator(selector)
                    if await return_radio.count() > 0:
                        await return_radio.first.click()
                        await page.wait_for_timeout(1000)
                        logger.info(f"Selected return journey using: {selector}")
                        break
                        
            except Exception as e:
                logger.warning(f"Could not select return journey explicitly: {e}")
            
            # Select departure port (Troon)
            logger.info("Selecting departure port: Troon...")
            departure_selectors = [
                'select[name="departurePort"]',
                '#departurePort', 
                '.departure-port select',
                'select:has(option:text("Troon"))'
            ]
            
            departure_selected = False
            for selector in departure_selectors:
                try:
                    await page.wait_for_selector(selector, timeout=5000)
                    departure_select = page.locator(selector).first
                    await departure_select.select_option(label='Troon')
                    await page.wait_for_timeout(1000)
                    logger.info(f"Selected Troon using: {selector}")
                    departure_selected = True
                    break
                except Exception as e:
                    logger.debug(f"Failed to select departure with {selector}: {e}")
                    
            if not departure_selected:
                raise Exception("Could not select departure port (Troon)")
            
            # Select arrival port (Brodick)
            logger.info("Selecting arrival port: Brodick...")
            arrival_selectors = [
                'select[name="arrivalPort"]',
                '#arrivalPort',
                '.arrival-port select',
                'select:has(option:text("Brodick"))'
            ]
            
            arrival_selected = False
            for selector in arrival_selectors:
                try:
                    await page.wait_for_selector(selector, timeout=5000)
                    arrival_select = page.locator(selector).first
                    await arrival_select.select_option(label='Brodick')
                    await page.wait_for_timeout(1000)
                    logger.info(f"Selected Brodick using: {selector}")
                    arrival_selected = True
                    break
                except Exception as e:
                    logger.debug(f"Failed to select arrival with {selector}: {e}")
                    
            if not arrival_selected:
                raise Exception("Could not select arrival port (Brodick)")
            
            # Set outbound date (Sunday, 3 August 2025)
            logger.info("Setting outbound date: 03/08/2025...")
            date_selectors = [
                'input[name="departureDate"]',
                '#departureDate',
                '.outbound-date input',
                'input[type="date"]'
            ]
            
            date_set = False
            for selector in date_selectors:
                try:
                    outbound_date_input = page.locator(selector).first
                    if await outbound_date_input.count() > 0:
                        await outbound_date_input.clear()
                        await outbound_date_input.fill('2025-08-03')  # Try ISO format first
                        await page.wait_for_timeout(500)
                        # If that doesn't work, try different formats
                        current_value = await outbound_date_input.input_value()
                        if not current_value or current_value == '':
                            await outbound_date_input.fill('03/08/2025')
                        await page.wait_for_timeout(1000)
                        logger.info(f"Set outbound date using: {selector}")
                        date_set = True
                        break
                except Exception as e:
                    logger.debug(f"Failed to set outbound date with {selector}: {e}")
                    
            if not date_set:
                logger.warning("Could not set outbound date")
            
            # Set return date (Tuesday, 5 August 2025)
            logger.info("Setting return date: 05/08/2025...")
            return_date_selectors = [
                'input[name="returnDate"]',
                '#returnDate',
                '.return-date input',
                'input[type="date"]:nth-of-type(2)'
            ]
            
            return_date_set = False
            for selector in return_date_selectors:
                try:
                    return_date_input = page.locator(selector).first
                    if await return_date_input.count() > 0:
                        await return_date_input.clear()
                        await return_date_input.fill('2025-08-05')  # Try ISO format first
                        await page.wait_for_timeout(500)
                        # If that doesn't work, try different formats
                        current_value = await return_date_input.input_value()
                        if not current_value or current_value == '':
                            await return_date_input.fill('05/08/2025')
                        await page.wait_for_timeout(1000)
                        logger.info(f"Set return date using: {selector}")
                        return_date_set = True
                        break
                except Exception as e:
                    logger.debug(f"Failed to set return date with {selector}: {e}")
                    
            if not return_date_set:
                logger.warning("Could not set return date")
            
            # Set passengers
            logger.info("Setting passenger details...")
            
            # Adults (1)
            adult_selectors = ['input[name="adults"]', '#adults', '.adults-count input', 'input[placeholder*="Adult"]']
            for selector in adult_selectors:
                try:
                    adult_input = page.locator(selector).first
                    if await adult_input.count() > 0:
                        await adult_input.clear()
                        await adult_input.fill('1')
                        logger.info(f"Set adults using: {selector}")
                        break
                except Exception as e:
                    logger.debug(f"Failed to set adults with {selector}: {e}")
            
            # Children (1)
            child_selectors = ['input[name="children"]', '#children', '.children-count input', 'input[placeholder*="Child"]']
            for selector in child_selectors:
                try:
                    child_input = page.locator(selector).first
                    if await child_input.count() > 0:
                        await child_input.clear()
                        await child_input.fill('1')
                        logger.info(f"Set children using: {selector}")
                        break
                except Exception as e:
                    logger.debug(f"Failed to set children with {selector}: {e}")
            
            # Infants (1)
            infant_selectors = ['input[name="infants"]', '#infants', '.infants-count input', 'input[placeholder*="Infant"]']
            for selector in infant_selectors:
                try:
                    infant_input = page.locator(selector).first
                    if await infant_input.count() > 0:
                        await infant_input.clear()
                        await infant_input.fill('1')
                        logger.info(f"Set infants using: {selector}")
                        break
                except Exception as e:
                    logger.debug(f"Failed to set infants with {selector}: {e}")
            
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
            search_selectors = [
                'button:has-text("Search")',
                'input[type="submit"]',
                '.search-button',
                '#searchButton',
                'button[type="submit"]',
                '.btn-search'
            ]
            
            search_submitted = False
            for selector in search_selectors:
                try:
                    search_btn = page.locator(selector).first
                    if await search_btn.count() > 0:
                        await search_btn.click()
                        logger.info(f"Clicked search using: {selector}")
                        search_submitted = True
                        break
                except Exception as e:
                    logger.debug(f"Failed to click search with {selector}: {e}")
                    
            if not search_submitted:
                raise Exception("Could not submit search form")
            
            # Wait for results page to load
            logger.info("Waiting for search results...")
            await page.wait_for_timeout(8000)
            
            # Wait for either results or error messages
            try:
                await page.wait_for_selector('.results, .ferry-results, .availability, .no-availability, .error-message', timeout=30000)
            except PlaywrightTimeoutError:
                logger.warning("Results page did not load within timeout")
                # Take screenshot for debugging
                await page.screenshot(path=f'logs/timeout_screenshot_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png')
                
            # Check for availability
            logger.info("Checking ferry availability...")
            
            # Take a screenshot for debugging
            await page.screenshot(path=f'logs/results_screenshot_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png')
            
            # Get page content for analysis
            page_content = await page.content()
            page_text = await page.inner_text('body')
            
            # Log some page content for debugging
            logger.info(f"Page title: {await page.title()}")
            logger.info(f"Current URL: {page.url}")
            
            # Look for availability indicators
            availability_found = False
            
            # Enhanced selectors for availability
            availability_selectors = [
                '.available',
                '.booking-available', 
                'button:has-text("Book")',
                'button:has-text("Select")',
                'button:has-text("Continue")',
                '.ferry-available',
                '[data-available="true"]',
                '.price',  # Often indicates available bookings
                '.fare'    # Similar to price
            ]
            
            for selector in availability_selectors:
                try:
                    available_elements = page.locator(selector)
                    count = await available_elements.count()
                    if count > 0:
                        availability_found = True
                        logger.info(f"Found {count} availability indicators using selector: {selector}")
                        break
                except Exception as e:
                    logger.debug(f"Error checking selector {selector}: {e}")
            
            # Check for unavailability indicators
            unavailable_selectors = [
                ':has-text("Not Available")',
                ':has-text("Sold Out")',
                ':has-text("No availability")',
                ':has-text("Fully booked")',
                '.unavailable',
                '.sold-out',
                '.no-availability'
            ]
            
            unavailable_found = False
            for selector in unavailable_selectors:
                try:
                    unavailable_elements = page.locator(selector)
                    count = await unavailable_elements.count()
                    if count > 0:
                        unavailable_found = True
                        logger.info(f"Found {count} unavailability indicators using selector: {selector}")
                        break
                except Exception as e:
                    logger.debug(f"Error checking unavailable selector {selector}: {e}")
            
            # Also check page text for keywords
            availability_keywords = ['available', 'book now', 'select', 'continue', 'price', 'fare']
            unavailable_keywords = ['not available', 'sold out', 'no availability', 'fully booked']
            
            page_text_lower = page_text.lower()
            
            for keyword in availability_keywords:
                if keyword in page_text_lower:
                    logger.info(f"Found availability keyword: {keyword}")
                    if not unavailable_found:  # Only set if we haven't found unavailable indicators
                        availability_found = True
                    break
                    
            for keyword in unavailable_keywords:
                if keyword in page_text_lower:
                    logger.info(f"Found unavailability keyword: {keyword}")
                    unavailable_found = True
                    break
            
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
