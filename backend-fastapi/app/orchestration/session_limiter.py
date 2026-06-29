from typing import Optional, Tuple

SESSION_FREQUENCY_CONFIG = {
    'daily_session_soft_limit': 2,
    'daily_session_hard_limit': 5,
    'weekly_referral_prompt_threshold': 7,
}

class SessionFrequencyLimiter:
    @staticmethod
    def check_limit(session_count_today: int, session_count_this_week: int) -> Tuple[bool, bool, Optional[str]]:
        """
        Checks daily and weekly session limits.
        Returns:
            allow_start (bool): True if session can proceed.
            show_referral_prompt (bool): True if we should display crisis/specialist/break advice.
            message (str or None): Rejection or advice message.
        """
        if session_count_today >= SESSION_FREQUENCY_CONFIG['daily_session_hard_limit']:
            return False, False, "Daily hard limit reached. Please take a break and come back tomorrow."
        
        if session_count_today >= SESSION_FREQUENCY_CONFIG['daily_session_soft_limit']:
            return True, True, "You've completed multiple sessions today. Taking a break or connecting with a specialist might be helpful."
            
        if session_count_this_week >= SESSION_FREQUENCY_CONFIG['weekly_referral_prompt_threshold']:
            return True, True, "You've had a highly active week. We suggest considering supplemental human counseling resources."
            
        return True, False, None
