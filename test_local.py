#!/usr/bin/env python3
"""
Test script for CalMac Ferry Checker
Use this to test the automation locally before deploying
"""

import os
import asyncio
from check_availability import check_ferry_availability, setup_logging

async def test_ferry_checker():
    """Test the ferry checker with debug output"""
    logger = setup_logging()
    
    # Set dummy credentials for testing (won't send actual messages)
    os.environ['TELEGRAM_BOT_TOKEN'] = 'test_token'
    os.environ['TELEGRAM_CHAT_ID'] = 'test_chat_id'
    
    logger.info("🧪 Starting test run of CalMac ferry checker...")
    logger.info("Note: This is a test run - no actual Telegram messages will be sent")
    
    try:
        result = await check_ferry_availability()
        if result:
            logger.info("✅ Test completed: Availability found!")
        else:
            logger.info("❌ Test completed: No availability found")
    except Exception as e:
        logger.error(f"❌ Test failed with error: {e}")
        
    logger.info("🧪 Test run completed. Check the logs/ directory for screenshots and detailed logs.")

if __name__ == "__main__":
    asyncio.run(test_ferry_checker())
