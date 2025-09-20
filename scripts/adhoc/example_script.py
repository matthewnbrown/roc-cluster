"""
Example adhoc script to demonstrate the system
"""

import logging

logger = logging.getLogger(__name__)

def main():
    """Example function that will be called automatically"""
    logger.info("This is an example adhoc script that runs once during startup")
    logger.info("This script would typically contain database migrations or setup code")
