"""
All Audiobook Categories (Section 4).
Complete MAM category and timespan support.
"""

import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

class MAMCategories:
    """
    Defines all MAM audiobook categories and timespans.
    """
    
    # All MAM Audiobook Categories (Section 4)
    CATEGORIES = {
        # Fiction
        'Fantasy': 'cat[]=74',
        'Science Fiction': 'cat[]=75',
        'Mystery': 'cat[]=76',
        'Thriller': 'cat[]=77',
        'Horror': 'cat[]=78',
        'Romance': 'cat[]=79',
        'Historical Fiction': 'cat[]=80',
        'Literary Fiction': 'cat[]=81',
        'Contemporary Fiction': 'cat[]=82',
        'Classics': 'cat[]=83',
        'Young Adult': 'cat[]=84',
        'Children': 'cat[]=85',
        'Short Stories': 'cat[]=86',
        'Poetry': 'cat[]=87',
        'Drama': 'cat[]=88',
        'Humor': 'cat[]=89',
        'Adventure': 'cat[]=90',
        'Western': 'cat[]=91',
        'Crime': 'cat[]=92',
        'Suspense': 'cat[]=93',
        
        # Non-Fiction
        'Biography': 'cat[]=94',
        'Autobiography': 'cat[]=95',
        'Memoir': 'cat[]=96',
        'History': 'cat[]=97',
        'Science': 'cat[]=98',
        'Philosophy': 'cat[]=99',
        'Religion': 'cat[]=100',
        'Self-Help': 'cat[]=101',
        'Business': 'cat[]=102',
        'Psychology': 'cat[]=103',
        'True Crime': 'cat[]=104',
        'Travel': 'cat[]=105',
        'Food & Cooking': 'cat[]=106',
        'Art': 'cat[]=107',
        'Music': 'cat[]=108',
        'Sports': 'cat[]=109',
        'Politics': 'cat[]=110',
        'Technology': 'cat[]=111',
        'Education': 'cat[]=112',
        'Health': 'cat[]=113'
    }
    
    # Timespans
    TIMESPANS = {
        'TODAY': 'tor[searchIn]=today',
        'WEEK': 'tor[searchIn]=week',
        'MONTH': 'tor[searchIn]=month',
        '3MONTH': 'tor[searchIn]=3month',
        '6MONTH': 'tor[searchIn]=6month',
        'YEAR': 'tor[searchIn]=year',
        'ALL': 'tor[searchIn]=all'
    }
    
    # Priority categories (for focused downloading)
    PRIORITY_CATEGORIES = [
        'Fantasy',
        'Science Fiction',
        'Mystery',
        'Thriller',
        'Horror',
        'Biography',
        'History',
        'Science'
    ]
    
    @classmethod
    def get_category_url_param(cls, category_name: str) -> str:
        """
        Get URL parameter for a category.
        
        Args:
            category_name: Category name (e.g., 'Fantasy')
            
        Returns:
            URL parameter string
        """
        return cls.CATEGORIES.get(category_name, '')
    
    @classmethod
    def get_timespan_url_param(cls, timespan: str) -> str:
        """
        Get URL parameter for a timespan.
        
        Args:
            timespan: Timespan key (e.g., 'WEEK')
            
        Returns:
            URL parameter string
        """
        return cls.TIMESPANS.get(timespan, cls.TIMESPANS['WEEK'])
    
    @classmethod
    def build_search_url(cls, 
                        category: str,
                        timespan: str = 'WEEK',
                        sort: str = 'seeders',
                        base_url: str = 'https://www.myanonamouse.net/tor/browse.php') -> str:
        """
        Build complete MAM search URL.
        
        Args:
            category: Category name
            timespan: Timespan key
            sort: Sort order ('seeders', 'added', 'size')
            base_url: MAM browse base URL
            
        Returns:
            Complete search URL
        """
        cat_param = cls.get_category_url_param(category)
        time_param = cls.get_timespan_url_param(timespan)
        
        if not cat_param:
            logger.error(f"Unknown category: {category}")
            return ''
        
        # Build URL
        url = f"{base_url}?{cat_param}&{time_param}"
        url += f"&tor[sortType]={sort}"
        url += "&tor[srchIn][title]=true"
        url += "&tor[srchIn][author]=true"
        url += "&tor[browseFlagsHideVsShow]=0"  # Show all
        
        return url
    
    @classmethod
    def get_all_categories(cls) -> List[str]:
        """Get list of all category names."""
        return list(cls.CATEGORIES.keys())
    
    @classmethod
    def get_priority_categories(cls) -> List[str]:
        """Get list of priority category names."""
        return cls.PRIORITY_CATEGORIES.copy()
    
    @classmethod
    def get_fiction_categories(cls) -> List[str]:
        """Get list of fiction category names."""
        fiction = [
            'Fantasy', 'Science Fiction', 'Mystery', 'Thriller', 'Horror',
            'Romance', 'Historical Fiction', 'Literary Fiction',
            'Contemporary Fiction', 'Classics', 'Young Adult', 'Children',
            'Short Stories', 'Poetry', 'Drama', 'Humor', 'Adventure',
            'Western', 'Crime', 'Suspense'
        ]
        return fiction
    
    @classmethod
    def get_nonfiction_categories(cls) -> List[str]:
        """Get list of non-fiction category names."""
        nonfiction = [
            'Biography', 'Autobiography', 'Memoir', 'History', 'Science',
            'Philosophy', 'Religion', 'Self-Help', 'Business', 'Psychology',
            'True Crime', 'Travel', 'Food & Cooking', 'Art', 'Music',
            'Sports', 'Politics', 'Technology', 'Education', 'Health'
        ]
        return nonfiction
    
    @classmethod
    def categorize_by_type(cls) -> Dict[str, List[str]]:
        """
        Categorize all categories by type.
        
        Returns:
            Dict with 'fiction' and 'nonfiction' lists
        """
        return {
            'fiction': cls.get_fiction_categories(),
            'nonfiction': cls.get_nonfiction_categories(),
            'priority': cls.get_priority_categories()
        }
    
    @classmethod
    def get_category_config(cls, category: str) -> Dict:
        """
        Get configuration for a specific category.
        
        Args:
            category: Category name
            
        Returns:
            Dict with category config
        """
        is_fiction = category in cls.get_fiction_categories()
        is_priority = category in cls.PRIORITY_CATEGORIES
        
        return {
            'name': category,
            'url_param': cls.get_category_url_param(category),
            'type': 'fiction' if is_fiction else 'nonfiction',
            'priority': is_priority,
            'default_timespan': 'WEEK' if is_priority else 'MONTH',
            'default_limit': 10 if is_priority else 5
        }


class CategoryScheduler:
    """
    Schedules category processing based on priority and timespan.
    """
    
    def __init__(self):
        self.categories = MAMCategories()
    
    def get_daily_schedule(self) -> List[Dict]:
        """
        Get daily processing schedule.
        
        Returns:
            List of category configs to process daily
        """
        schedule = []
        
        # Priority categories: Daily, WEEK timespan
        for cat in self.categories.get_priority_categories():
            schedule.append({
                'category': cat,
                'timespan': 'WEEK',
                'limit': 10,
                'frequency': 'daily'
            })
        
        return schedule
    
    def get_weekly_schedule(self) -> List[Dict]:
        """
        Get weekly processing schedule.
        
        Returns:
            List of category configs to process weekly
        """
        schedule = []
        
        # All categories: Weekly, MONTH timespan
        for cat in self.categories.get_all_categories():
            if cat not in self.categories.get_priority_categories():
                schedule.append({
                    'category': cat,
                    'timespan': 'MONTH',
                    'limit': 5,
                    'frequency': 'weekly'
                })
        
        return schedule
    
    def get_monthly_schedule(self) -> List[Dict]:
        """
        Get monthly processing schedule.
        
        Returns:
            List of category configs to process monthly
        """
        schedule = []
        
        # All categories: Monthly, 3MONTH timespan
        for cat in self.categories.get_all_categories():
            schedule.append({
                'category': cat,
                'timespan': '3MONTH',
                'limit': 20,
                'frequency': 'monthly'
            })
        
        return schedule
    
    def get_full_schedule(self) -> Dict[str, List[Dict]]:
        """
        Get complete processing schedule.
        
        Returns:
            Dict with 'daily', 'weekly', 'monthly' schedules
        """
        return {
            'daily': self.get_daily_schedule(),
            'weekly': self.get_weekly_schedule(),
            'monthly': self.get_monthly_schedule()
        }
