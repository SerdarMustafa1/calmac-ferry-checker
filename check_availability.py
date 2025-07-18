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
        logger.warning("Telegram credentials not found in environment variables (normal for local testing)")
        logger.info(f"Would send Telegram message: {message}")
        return True  # Return True for local testing
    
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
            headless=True,  # Back to headless for production
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor'
            ]
        )
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 720},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        page = await context.new_page()
        
        # Add retry logic
        max_retries = 2
        for attempt in range(max_retries):
            try:
                logger.info(f"Attempt {attempt + 1} of {max_retries}")
                
                # Navigate to CalMac welcoming page
                logger.info("Navigating to CalMac welcoming page...")
                await page.goto('https://ticketing.calmac.co.uk/B2C-Calmac/#/auth/welcoming', 
                              wait_until='domcontentloaded', timeout=45000)
                
                # Wait for page to load completely and take initial screenshot
                await page.wait_for_timeout(8000)
                await page.screenshot(path=f'logs/initial_page_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png')
                
                # Log page info for debugging
                logger.info(f"Page title: {await page.title()}")
                logger.info(f"Current URL: {page.url}")
                
                # Wait for and look for the main booking interface
                booking_selectors = [
                    'button:has-text("Start booking")',
                    'button:has-text("Book")',
                    'a:has-text("Start")',
                    '.start-booking',
                    '.booking-button',
                    'button[data-testid*="start"]',
                    'button[data-testid*="book"]'
                ]
                
                start_button_found = False
                for selector in booking_selectors:
                    try:
                        await page.wait_for_selector(selector, timeout=5000)
                        await page.click(selector)
                        logger.info(f"Clicked start booking button using: {selector}")
                        start_button_found = True
                        await page.wait_for_timeout(3000)
                        break
                    except PlaywrightTimeoutError:
                        continue
                        
                if not start_button_found:
                    # Try to navigate directly to the booking form
                    logger.info("No start button found, trying direct navigation to booking form...")
                    await page.goto('https://ticketing.calmac.co.uk/B2C-Calmac/#/desktop/step1/destinations/single', 
                                  wait_until='domcontentloaded', timeout=30000)
                    await page.wait_for_timeout(5000)
                
                # Take screenshot after navigation
                await page.screenshot(path=f'logs/booking_page_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png')
                
                # Debug: Log all available form elements
                logger.info("=== DEBUG: Available form elements ===")
                try:
                    all_inputs = await page.locator('input, select, edea-select, ion-select, button').all()
                    logger.info(f"Found {len(all_inputs)} form elements")
                    
                    for i, element in enumerate(all_inputs[:10]):  # Log first 10 elements
                        try:
                            tag_name = await element.evaluate('el => el.tagName')
                            attrs = await element.evaluate('el => Array.from(el.attributes).map(attr => `${attr.name}="${attr.value}"`).join(" ")')
                            text_content = await element.text_content()
                            if text_content:
                                text_content = text_content.strip()[:50]  # First 50 chars
                            logger.info(f"Element {i+1}: <{tag_name.lower()} {attrs}>{text_content or ''}</{tag_name.lower()}>")
                        except:
                            logger.info(f"Element {i+1}: Could not analyze")
                except Exception as e:
                    logger.debug(f"Debug element listing failed: {e}")
                logger.info("=== END DEBUG ===")
                
                # Look for the return journey option
                logger.info("Looking for return journey option...")
                return_selectors = [
                    'input[type="radio"][value="return"]',
                    'input[name="journeyType"][value="return"]',
                    'label:has-text("Return") input',
                    'button:has-text("Return")',
                    '.return-journey input',
                    '.journey-type input[value="return"]'
                ]
                
                for selector in return_selectors:
                    try:
                        return_element = page.locator(selector)
                        if await return_element.count() > 0:
                            await return_element.first.click()
                            logger.info(f"Selected return journey using: {selector}")
                            await page.wait_for_timeout(2000)
                            break
                    except Exception as e:
                        logger.debug(f"Failed to select return journey with {selector}: {e}")
                
                # Select departure port (Troon)
                logger.info("Looking for departure port selection...")
                await page.wait_for_timeout(2000)
                
                # Updated selectors for Angular/Ionic components
                departure_selectors = [
                    'edea-select[data-testid*="departure"]',
                    'edea-select[data-testid*="from"]', 
                    'ion-select[placeholder*="departure"]',
                    'ion-select[placeholder*="from"]',
                    'edea-select:has([placeholder*="From"])',
                    'edea-select:has([placeholder*="Departure"])',
                    'select[name*="departure"]',
                    'select[name*="from"]',
                    '#departurePort',
                    '.departure select',
                    '.from-port select'
                ]
                
                departure_selected = False
                for selector in departure_selectors:
                    try:
                        logger.info(f"Trying departure selector: {selector}")
                        elements = page.locator(selector)
                        count = await elements.count()
                        
                        if count > 0:
                            # For edea-select and ion-select components, try clicking first
                            element = elements.first
                            if 'edea-select' in selector or 'ion-select' in selector:
                                await element.click()
                                await page.wait_for_timeout(1000)
                                
                                # Look for dropdown options
                                option_selectors = [
                                    'ion-item:has-text("Troon")',
                                    'div[role="option"]:has-text("Troon")',
                                    '.select-option:has-text("Troon")',
                                    'button:has-text("Troon")'
                                ]
                                
                                for option_selector in option_selectors:
                                    try:
                                        option_elements = page.locator(option_selector)
                                        if await option_elements.count() > 0:
                                            await option_elements.first.click()
                                            logger.info(f"Selected Troon using: {selector} -> {option_selector}")
                                            departure_selected = True
                                            break
                                    except Exception as e:
                                        logger.debug(f"Failed to click Troon option with {option_selector}: {e}")
                                
                                if departure_selected:
                                    break
                            else:
                                # Traditional select elements
                                try:
                                    await element.select_option(label='Troon')
                                    logger.info(f"Selected Troon by label using: {selector}")
                                    departure_selected = True
                                    break
                                except:
                                    try:
                                        await element.select_option(value='troon')
                                        logger.info(f"Selected Troon by value using: {selector}")
                                        departure_selected = True
                                        break
                                    except:
                                        continue
                                
                    except Exception as e:
                        logger.debug(f"Failed with departure selector {selector}: {e}")
                
                if departure_selected:
                    await page.wait_for_timeout(2000)
                else:
                    logger.warning("Could not select departure port (Troon)")
                
                # Select arrival port (Brodick)
                logger.info("Looking for arrival port selection...")
                await page.wait_for_timeout(2000)
                
                arrival_selectors = [
                    'edea-select[data-testid*="arrival"]',
                    'edea-select[data-testid*="to"]',
                    'ion-select[placeholder*="arrival"]', 
                    'ion-select[placeholder*="to"]',
                    'edea-select:has([placeholder*="To"])',
                    'edea-select:has([placeholder*="Arrival"])',
                    'select[name*="arrival"]',
                    'select[name*="to"]',
                    '#arrivalPort',
                    '.arrival select',
                    '.to-port select'
                ]
                
                arrival_selected = False
                for selector in arrival_selectors:
                    try:
                        logger.info(f"Trying arrival selector: {selector}")
                        elements = page.locator(selector)
                        count = await elements.count()
                        
                        if count > 0:
                            element = elements.first
                            if 'edea-select' in selector or 'ion-select' in selector:
                                await element.click()
                                await page.wait_for_timeout(1000)
                                
                                # Look for dropdown options
                                option_selectors = [
                                    'ion-item:has-text("Brodick")',
                                    'div[role="option"]:has-text("Brodick")',
                                    '.select-option:has-text("Brodick")',
                                    'button:has-text("Brodick")'
                                ]
                                
                                for option_selector in option_selectors:
                                    try:
                                        option_elements = page.locator(option_selector)
                                        if await option_elements.count() > 0:
                                            await option_elements.first.click()
                                            logger.info(f"Selected Brodick using: {selector} -> {option_selector}")
                                            arrival_selected = True
                                            break
                                    except Exception as e:
                                        logger.debug(f"Failed to click Brodick option with {option_selector}: {e}")
                                
                                if arrival_selected:
                                    break
                            else:
                                # Traditional select elements
                                try:
                                    await element.select_option(label='Brodick')
                                    logger.info(f"Selected Brodick by label using: {selector}")
                                    arrival_selected = True
                                    break
                                except:
                                    try:
                                        await element.select_option(value='brodick')
                                        logger.info(f"Selected Brodick by value using: {selector}")
                                        arrival_selected = True
                                        break
                                    except:
                                        continue
                                
                    except Exception as e:
                        logger.debug(f"Failed with arrival selector {selector}: {e}")
                
                if arrival_selected:
                    await page.wait_for_timeout(2000)
                else:
                    logger.warning("Could not select arrival port (Brodick)")
                
                # Set outbound date (Sunday, 3 August 2025)
                logger.info("Setting outbound date: 03/08/2025...")
                await page.wait_for_timeout(2000)
                
                outbound_date_selectors = [
                    'ion-datetime[data-testid*="departure"]',
                    'ion-datetime[data-testid*="outbound"]',
                    'edea-datepicker[data-testid*="departure"]',
                    'edea-datepicker[data-testid*="outbound"]',
                    'input[name*="departure"][type="date"]',
                    'input[name*="outbound"][type="date"]',
                    'input[data-testid*="departure"]',
                    'input[data-testid*="outbound"]',
                    '#departureDate',
                    '.departure-date input',
                    '.outbound-date input',
                    'input[type="date"]:first-of-type'
                ]
                
                outbound_date_set = False
                for selector in outbound_date_selectors:
                    try:
                        elements = page.locator(selector)
                        if await elements.count() > 0:
                            element = elements.first
                            
                            if 'ion-datetime' in selector or 'edea-datepicker' in selector:
                                # For Ionic datetime components
                                await element.click()
                                await page.wait_for_timeout(1000)
                                # Try to set the value attribute directly
                                await element.evaluate('el => el.value = "2025-08-03"')
                                await page.wait_for_timeout(500)
                                await element.dispatch_event('change')
                                logger.info(f"Set outbound date using Ionic component: {selector}")
                                outbound_date_set = True
                                break
                            else:
                                # Traditional input elements
                                await element.clear()
                                await element.fill('2025-08-03')  # ISO format
                                await page.wait_for_timeout(1000)
                                
                                # Verify it was set
                                value = await element.input_value()
                                if value and ('2025-08-03' in value or '03/08/2025' in value):
                                    logger.info(f"Set outbound date using: {selector}")
                                    outbound_date_set = True
                                    break
                                else:
                                    # Try different format
                                    await element.clear()
                                    await element.fill('03/08/2025')
                                    await page.wait_for_timeout(1000)
                                    value = await element.input_value()
                                    if value:
                                        logger.info(f"Set outbound date (DD/MM/YYYY) using: {selector}")
                                        outbound_date_set = True
                                        break
                                    
                    except Exception as e:
                        logger.debug(f"Failed to set outbound date with {selector}: {e}")
                
                if not outbound_date_set:
                    logger.warning("Could not set outbound date")
                
                # Set return date (Tuesday, 5 August 2025)
                logger.info("Setting return date: 05/08/2025...")
                await page.wait_for_timeout(2000)
                
                return_date_selectors = [
                    'input[name*="return"][type="date"]',
                    'input[name*="arrival"][type="date"]',
                    'input[data-testid*="return"]',
                    'input[data-testid*="arrival"]',
                    '#returnDate',
                    '.return-date input',
                    '.arrival-date input',
                    'input[type="date"]:nth-of-type(2)',
                    'input[type="date"]:last-of-type'
                ]
                
                return_date_set = False
                for selector in return_date_selectors:
                    try:
                        elements = page.locator(selector)
                        if await elements.count() > 0:
                            element = elements.first
                            await element.clear()
                            await element.fill('2025-08-05')  # ISO format
                            await page.wait_for_timeout(1000)
                            
                            # Verify it was set
                            value = await element.input_value()
                            if value and ('2025-08-05' in value or '05/08/2025' in value):
                                logger.info(f"Set return date using: {selector}")
                                return_date_set = True
                                break
                            else:
                                # Try different format
                                await element.clear()
                                await element.fill('05/08/2025')
                                await page.wait_for_timeout(1000)
                                value = await element.input_value()
                                if value:
                                    logger.info(f"Set return date (DD/MM/YYYY) using: {selector}")
                                    return_date_set = True
                                    break
                                    
                    except Exception as e:
                        logger.debug(f"Failed to set return date with {selector}: {e}")
                
                if not return_date_set:
                    logger.warning("Could not set return date")
                
                # Set passengers
                logger.info("Setting passenger details...")
                await page.wait_for_timeout(2000)
                
                # Adults (1)
                adult_selectors = [
                    'input[name*="adult"]',
                    'input[data-testid*="adult"]',
                    'select[name*="adult"]',
                    '#adults',
                    '.adults input',
                    '.passenger input:first-of-type'
                ]
                
                for selector in adult_selectors:
                    try:
                        elements = page.locator(selector)
                        if await elements.count() > 0:
                            element = elements.first
                            if await element.get_attribute('type') == 'number' or 'input' in selector:
                                await element.clear()
                                await element.fill('1')
                            else:  # select element
                                await element.select_option('1')
                            logger.info(f"Set adults to 1 using: {selector}")
                            break
                    except Exception as e:
                        logger.debug(f"Failed to set adults with {selector}: {e}")
                
                # Children (1)
                child_selectors = [
                    'input[name*="child"]',
                    'input[data-testid*="child"]',
                    'select[name*="child"]',
                    '#children',
                    '.children input'
                ]
                
                for selector in child_selectors:
                    try:
                        elements = page.locator(selector)
                        if await elements.count() > 0:
                            element = elements.first
                            if await element.get_attribute('type') == 'number' or 'input' in selector:
                                await element.clear()
                                await element.fill('1')
                            else:
                                await element.select_option('1')
                            logger.info(f"Set children to 1 using: {selector}")
                            break
                    except Exception as e:
                        logger.debug(f"Failed to set children with {selector}: {e}")
                
                # Infants (1)
                infant_selectors = [
                    'input[name*="infant"]',
                    'input[data-testid*="infant"]',
                    'select[name*="infant"]',
                    '#infants',
                    '.infants input'
                ]
                
                for selector in infant_selectors:
                    try:
                        elements = page.locator(selector)
                        if await elements.count() > 0:
                            element = elements.first
                            if await element.get_attribute('type') == 'number' or 'input' in selector:
                                await element.clear()
                                await element.fill('1')
                            else:
                                await element.select_option('1')
                            logger.info(f"Set infants to 1 using: {selector}")
                            break
                    except Exception as e:
                        logger.debug(f"Failed to set infants with {selector}: {e}")
                
                # Add vehicle (Car)
                logger.info("Adding vehicle: Car...")
                await page.wait_for_timeout(2000)
                
                # Look for add vehicle button first
                add_vehicle_selectors = [
                    'button:has-text("Add vehicle")',
                    'button:has-text("Add car")',
                    'button[data-testid*="vehicle"]',
                    '.add-vehicle',
                    '.vehicle-add'
                ]
                
                vehicle_section_opened = False
                for selector in add_vehicle_selectors:
                    try:
                        elements = page.locator(selector)
                        if await elements.count() > 0:
                            await elements.first.click()
                            logger.info(f"Clicked add vehicle button using: {selector}")
                            vehicle_section_opened = True
                            await page.wait_for_timeout(2000)
                            break
                    except Exception as e:
                        logger.debug(f"Failed to click add vehicle with {selector}: {e}")
                
                # Select car type
                car_selectors = [
                    'select[name*="vehicle"]',
                    'select[data-testid*="vehicle"]',
                    '#vehicleType',
                    '.vehicle-type select',
                    'select:has(option:text("Car"))'
                ]
                
                for selector in car_selectors:
                    try:
                        elements = page.locator(selector)
                        if await elements.count() > 0:
                            element = elements.first
                            try:
                                await element.select_option(label='Car')
                                logger.info(f"Selected Car using: {selector}")
                                break
                            except:
                                try:
                                    await element.select_option(value='car')
                                    logger.info(f"Selected car by value using: {selector}")
                                    break
                                except:
                                    continue
                    except Exception as e:
                        logger.debug(f"Failed to select car with {selector}: {e}")
                
                # Take screenshot before submitting
                await page.screenshot(path=f'logs/before_search_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png')
                
                # Submit the search
                logger.info("Submitting ferry search...")
                await page.wait_for_timeout(2000)
                
                search_selectors = [
                    'button:has-text("Search")',
                    'button:has-text("Find")',
                    'button[type="submit"]',
                    'input[type="submit"]',
                    'button[data-testid*="search"]',
                    '.search-button',
                    '.btn-search',
                    '.submit-button'
                ]
                
                search_submitted = False
                for selector in search_selectors:
                    try:
                        elements = page.locator(selector)
                        if await elements.count() > 0:
                            await elements.first.click()
                            logger.info(f"Clicked search using: {selector}")
                            search_submitted = True
                            break
                    except Exception as e:
                        logger.debug(f"Failed to click search with {selector}: {e}")
                
                if not search_submitted:
                    logger.warning("Could not submit search form")
                    # Try pressing Enter on the page
                    await page.keyboard.press('Enter')
                    logger.info("Tried pressing Enter to submit")
                
                # Wait for results page to load
                logger.info("Waiting for search results...")
                await page.wait_for_timeout(10000)
                
                # Wait for results or error messages
                try:
                    await page.wait_for_selector(
                        '.results, .sailing-results, .availability, .no-availability, .error, .ferry-times, .timetable', 
                        timeout=30000
                    )
                except PlaywrightTimeoutError:
                    logger.warning("Results page did not load within timeout")
                
                # Take screenshot of results
                await page.screenshot(path=f'logs/results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png')
                
                # Check for availability
                logger.info("Checking ferry availability...")
                
                # Get page content for analysis
                page_content = await page.content()
                page_text = await page.inner_text('body')
                
                # Log page info
                logger.info(f"Results page title: {await page.title()}")
                logger.info(f"Results page URL: {page.url}")
                
                # Enhanced availability detection
                availability_found = False
                
                # Look for specific availability indicators
                availability_selectors = [
                    'button:has-text("Select")',
                    'button:has-text("Book")',
                    'button:has-text("Continue")',
                    'button:has-text("Choose")',
                    '.available',
                    '.booking-available',
                    '.select-sailing',
                    '.price',
                    '.fare',
                    '.sailing-time:has(.available)',
                    '[data-available="true"]',
                    '.timetable .available'
                ]
                
                availability_count = 0
                for selector in availability_selectors:
                    try:
                        elements = page.locator(selector)
                        count = await elements.count()
                        if count > 0:
                            availability_count += count
                            logger.info(f"Found {count} availability indicators using: {selector}")
                    except Exception as e:
                        logger.debug(f"Error checking availability selector {selector}: {e}")
                
                # Check for unavailability indicators
                unavailable_selectors = [
                    ':has-text("Not Available")',
                    ':has-text("Sold Out")',
                    ':has-text("Fully booked")',
                    ':has-text("No sailings")',
                    '.unavailable',
                    '.sold-out',
                    '.no-availability',
                    '.fully-booked'
                ]
                
                unavailable_count = 0
                for selector in unavailable_selectors:
                    try:
                        elements = page.locator(selector)
                        count = await elements.count()
                        if count > 0:
                            unavailable_count += count
                            logger.info(f"Found {count} unavailability indicators using: {selector}")
                    except Exception as e:
                        logger.debug(f"Error checking unavailability selector {selector}: {e}")
                
                # Text-based availability check
                availability_keywords = [
                    'select sailing', 'book now', 'available', 'choose time',
                    'price:', '£', 'fare', 'continue to booking'
                ]
                unavailable_keywords = [
                    'not available', 'sold out', 'fully booked', 'no sailings',
                    'no availability', 'service not operating'
                ]
                
                page_text_lower = page_text.lower()
                keyword_availability = 0
                keyword_unavailability = 0
                
                for keyword in availability_keywords:
                    if keyword in page_text_lower:
                        keyword_availability += 1
                        logger.info(f"Found availability keyword: '{keyword}'")
                
                for keyword in unavailable_keywords:
                    if keyword in page_text_lower:
                        keyword_unavailability += 1
                        logger.info(f"Found unavailability keyword: '{keyword}'")
                
                # Decision logic - need strong positive indicators
                if (availability_count >= 2 or keyword_availability >= 3) and unavailable_count == 0:
                    availability_found = True
                    logger.info("🎉 Strong indication of ferry availability found!")
                elif availability_count > 0 and unavailable_count == 0 and keyword_availability > 0:
                    availability_found = True
                    logger.info("🎉 Ferry availability found!")
                else:
                    logger.info(f"❌ No clear availability found. Availability indicators: {availability_count}, Unavailable indicators: {unavailable_count}")
                
                # Save detailed results for debugging
                with open(f'logs/results_content_{datetime.now().strftime("%Y%m%d_%H%M%S")}.html', 'w', encoding='utf-8') as f:
                    f.write(page_content)
                
                # If availability found, send Telegram notification
                if availability_found:
                    logger.info("🎉 Ferry availability FOUND!")
                    
                    message = f"""🚢 CalMac Alert! Your ferry is now available:

Outbound: Troon → Brodick on Sun 03 Aug @ 07:45  
Return: Brodick → Troon on Tue 05 Aug @ 15:30  
Passengers: 1 Adult, 1 Child, 1 Infant + Car

Book now: https://ticketing.calmac.co.uk/B2C-Calmac/

Checked at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}
Availability indicators found: {availability_count}
Keywords matched: {keyword_availability}"""
                    
                    send_telegram_message(message)
                    return True
                else:
                    logger.info("❌ No ferry availability found at this time")
                    
                    # Send notification for no availability as well
                    no_availability_message = f"""ℹ️ CalMac Check Complete - No Availability

Route: Troon → Brodick (03 Aug) / Brodick → Troon (05 Aug)
Passengers: 1 Adult, 1 Child, 1 Infant + Car

Status: No availability found at this time
Will check again in 1 hour

Checked at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}"""
                    
                    send_telegram_message(no_availability_message)
                    return False
                
            except PlaywrightTimeoutError as e:
                logger.error(f"Timeout error on attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    logger.info("Retrying...")
                    await page.wait_for_timeout(5000)
                    continue
                else:
                    return False
            except Exception as e:
                logger.error(f"Error on attempt {attempt + 1}: {e}")
                # Take screenshot on error
                try:
                    await page.screenshot(path=f'logs/error_attempt_{attempt + 1}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png')
                except:
                    pass
                if attempt < max_retries - 1:
                    logger.info("Retrying...")
                    await page.wait_for_timeout(5000)
                    continue
                else:
                    return False
        
        await browser.close()
        return False

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
