#!/usr/bin/env python3
"""
End-to-End Integration Test Suite
Tests MAMcrawler + Frank Audiobook Hub integration with real data
"""

import asyncio
import sys
import json
from datetime import datetime
from typing import Dict, List, Tuple

# Add backend to path
sys.path.insert(0, 'backend')

from dotenv import load_dotenv
import os
import aiohttp
import logging

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

class IntegrationTestSuite:
    """Complete end-to-end test suite for MAMcrawler + Frank"""
    
    def __init__(self):
        # Configuration from .env
        self.abs_url = os.getenv('ABS_URL', 'http://localhost:13378')
        self.abs_token = os.getenv('ABS_TOKEN')
        self.qb_url = os.getenv('QBITTORRENT_URL', 'http://192.168.0.48:52095')
        self.qb_user = os.getenv('QBITTORRENT_USERNAME')
        self.qb_pass = os.getenv('QBITTORRENT_PASSWORD')
        self.prowlarr_url = os.getenv('PROWLARR_URL', 'http://localhost:9696')
        self.prowlarr_key = os.getenv('PROWLARR_API_KEY')
        
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'tests': [],
            'summary': {}
        }
    
    async def test_abs_connectivity(self) -> Tuple[bool, str]:
        """Test AudiobookShelf API connectivity"""
        logger.info("Testing AudiobookShelf connectivity...")
        try:
            async with aiohttp.ClientSession() as session:
                headers = {'Authorization': f'Bearer {self.abs_token}'}
                async with session.get(f'{self.abs_url}/api/libraries', headers=headers, ssl=False) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        lib_count = len(data.get('libraries', []))
                        return True, f"Connected. Found {lib_count} libraries"
                    else:
                        return False, f"HTTP {resp.status}"
        except Exception as e:
            return False, str(e)
    
    async def test_qbittorrent_connectivity(self) -> Tuple[bool, str]:
        """Test qBittorrent API connectivity"""
        logger.info("Testing qBittorrent connectivity...")
        try:
            async with aiohttp.ClientSession() as session:
                # Test login
                login_url = f'{self.qb_url}/api/v2/auth/login'
                from aiohttp import FormData
                data = FormData()
                data.add_field('username', self.qb_user)
                data.add_field('password', self.qb_pass)
                
                async with session.post(login_url, data=data, ssl=False) as resp:
                    if resp.status == 200:
                        # Get torrent count
                        torrents_url = f'{self.qb_url}/api/v2/torrents/info'
                        async with session.get(torrents_url, ssl=False) as t_resp:
                            if t_resp.status == 200:
                                torrents = await t_resp.json()
                                return True, f"Connected. {len(torrents)} torrents"
                            else:
                                return False, f"Torrents API HTTP {t_resp.status}"
                    else:
                        return False, f"Login HTTP {resp.status}"
        except Exception as e:
            return False, str(e)
    
    async def test_prowlarr_connectivity(self) -> Tuple[bool, str]:
        """Test Prowlarr API connectivity"""
        logger.info("Testing Prowlarr connectivity...")
        try:
            async with aiohttp.ClientSession() as session:
                url = f'{self.prowlarr_url}/api/v1/indexer'
                headers = {'X-Api-Key': self.prowlarr_key}
                async with session.get(url, headers=headers, ssl=False) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return True, f"Connected. {len(data)} indexers"
                    else:
                        return False, f"HTTP {resp.status}"
        except Exception as e:
            return False, str(e)
    
    async def test_frank_api_endpoints(self) -> Tuple[bool, str]:
        """Test Frank API endpoints"""
        logger.info("Testing Frank API endpoints...")
        try:
            frank_url = 'http://localhost:5000'  # Frank API port
            async with aiohttp.ClientSession() as session:
                endpoints = [
                    '/health',
                    '/api/audiobooks',
                    '/api/config',
                ]
                successful = 0
                for endpoint in endpoints:
                    try:
                        async with session.get(f'{frank_url}{endpoint}', ssl=False) as resp:
                            if resp.status == 200:
                                successful += 1
                    except:
                        pass
                
                if successful > 0:
                    return True, f"Accessible. {successful}/{len(endpoints)} endpoints working"
                else:
                    return False, "No endpoints responding"
        except Exception as e:
            return False, str(e)
    
    async def run_all_tests(self) -> Dict:
        """Run complete test suite"""
        logger.info("="*70)
        logger.info("END-TO-END INTEGRATION TEST SUITE")
        logger.info("="*70)
        
        tests = [
            ('AudiobookShelf', self.test_abs_connectivity),
            ('qBittorrent', self.test_qbittorrent_connectivity),
            ('Prowlarr', self.test_prowlarr_connectivity),
            ('Frank API', self.test_frank_api_endpoints),
        ]
        
        passed = 0
        failed = 0
        
        for test_name, test_func in tests:
            success, message = await test_func()
            status = "PASS" if success else "FAIL"
            logger.info(f"[{status}] {test_name}: {message}")
            
            self.results['tests'].append({
                'name': test_name,
                'status': status,
                'message': message
            })
            
            if success:
                passed += 1
            else:
                failed += 1
        
        self.results['summary'] = {
            'total_tests': len(tests),
            'passed': passed,
            'failed': failed,
            'success_rate': f"{(passed/len(tests)*100):.1f}%"
        }
        
        logger.info("="*70)
        logger.info(f"RESULTS: {passed}/{len(tests)} passed")
        logger.info("="*70)
        
        return self.results

async def main():
    """Main test execution"""
    suite = IntegrationTestSuite()
    results = await suite.run_all_tests()
    
    # Save results
    with open('integration_test_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    logger.info("Results saved to integration_test_results.json")
    
    # Exit with appropriate code
    if results['summary']['failed'] == 0:
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == '__main__':
    asyncio.run(main())
