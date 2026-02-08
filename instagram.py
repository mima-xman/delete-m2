from playwright.sync_api import sync_playwright
from playwright_helper import PlaywrightHelper
from re import search
from random import randint
from os.path import exists
from os import makedirs, getenv

from utils import get_2fa_code


IS_CI = getenv("CI", "false").lower() == "true"
# =====================================
# Browser settings
# =====================================
ASK_BEFORE_CLOSE_BROWSER = getenv("ASK_BEFORE_CLOSE_BROWSER", "false").lower() == "true"
HEADLESS = getenv("HEADLESS", "true").lower() == "true"
ARGS = [
    "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.90 Safari/537.36",
    # Set language
    "--lang=en-US"
]
VIEWPORT = {
    "width": 1080,
    "height": 720
}
# Browser executable paths
BRAVE_PATH = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"
GOOGLE_CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
CHROMIUM_PATH = r"C:\Program Files\Chromium\Application\chrome.exe"
BROWSER_PATH = getenv("BROWSER_PATH", GOOGLE_CHROME_PATH)
# Output folder
OUTPUT_FOLDER = r"instagram_outputs"

try:
    if not exists(OUTPUT_FOLDER):
        makedirs(OUTPUT_FOLDER)
        print(f"Output folder '{OUTPUT_FOLDER}' created successfully.")
    else:
        print(f"Output folder '{OUTPUT_FOLDER}' already exists.")
except Exception as e:
    print(f"An error occurred while creating the output folder '{OUTPUT_FOLDER}': {e}")

# =====================================
# Instagram settings
# =====================================
HOME_PAGE_URL = "https://www.instagram.com"
REELS_PAGE_URL = "https://www.instagram.com/reels"
NUMBER_OF_REELS_TO_WATCH = getenv("NUMBER_OF_REELS_TO_WATCH", 5)
MAX_ATTEMPTS_TO_MARK_REEL_AS_WATCHED = 3
SELECTORS = {
    "LOGIN": {
        "TYPE_1": {
            "USERNAME_FIELD": "input[name='email'], input:has(+ label:has-text('Mobile number, username or email'))",
            "PASSWORD_FIELD": "input[name='pass'], input:has(+ label:has-text('Password'))",
            "PASSWORD_ERROR": "span:has-text('The password you entered is incorrect.')",
            "LOGIN_BUTTON": "div[tabindex='0'][role='button']:has(span:has-text('Log in'))",
            "ERROR_MESSAGE": (
                "span:has-text('The login information you entered is incorrect.')"
                ", span:has(a:has-text('Find your account and log in.'))"
            ),
        },
    },
    "COMPLETE_2FA": {
        "TYPE_1": {
            "CODE_FIELD": "input[name='verificationCode'], label:has(span:has-text('Security Code')) input",
            "CONFIRM_BUTTON": "button:has-text('Confirm')",
        },
    },
    "INDICATORS": {
        "SUCCESS_LOGIN": "div[role='button']:has(title:has-text('Messages'))",
        "SUCCESS_LOGOUT": "div[role='button']:has(span:has-text('Use another profile'))", # also we can use url=https://www.instagram.com/?flo=true
    },
    "REEL_ACTIONS": {
        # Like and unlike
        "LIKE_BUTTON": "main > div > div:nth-child({reel_number}) div[role='button']:has(title:has-text('Like'))",
        "UNLIKE_BUTTON": "main > div > div:nth-child({reel_number}) div[role='button']:has(title:has-text('Unlike'))",
        # Save and unsave
        "SAVE_BUTTON": "main > div > div:nth-child({reel_number}) div[role='button']:has(title:has-text('Save'))",
        "UNSAVE_BUTTON": "main > div > div:nth-child({reel_number}) div[role='button']:has(title:has-text('Remove'))",
        # Repost
        "REPOST_BUTTON": "main > div > div:nth-child({reel_number}) div[role='button']:has(title:has-text('Repost'))",
        # Follow and unfollow
        "FOLLOW_BUTTON": "main > div > div:nth-child({reel_number}) div[role='presentation'] div[role='button'] div[role='button']:has-text('Follow')",
        "UNFOLLOW_BUTTON": "main > div > div:nth-child({reel_number}) div[role='presentation'] div[role='button'] div[role='button']:has-text('Following')",
    },
    "LOGOUT": {
        "SETTINGS_BUTTON": "a:has(title:has-text('Settings'))",
        "LOGOUT_BUTTON": "div[role='button']:has(span:has-text('Log out'))",
    }
}


class Instagram:
    def __init__(self, username, password, two_factor_code):
        self.username = username
        self.password = password
        self.two_factor_code = two_factor_code
        self.browser = None
        self.page = None
        self.screenshot_number = 1

    # =============================
    # Helper methods
    # =============================
    
    def _take_screenshot(self):
        try:
            self.page.screenshot(path=f"{OUTPUT_FOLDER}/screenshot_{self.screenshot_number}.png")
            self.screenshot_number += 1
            print("Screenshot taken successfully.")
        except Exception as e:
            print(f"An error occurred while taking a screenshot: {e}")

    
    # =============================
    # Login methods
    # =============================
    
    def _login_type_1(self):
        print("Using login type 1...")
        selectors = SELECTORS["LOGIN"]["TYPE_1"]

        login_type_1_actions = [
            {
                "name": "Fill username",
                "type": "fill",
                "selector": selectors["USERNAME_FIELD"],
                "value": self.username,
            },
            {
                "name": "Fill password",
                "type": "fill",
                "selector": selectors["PASSWORD_FIELD"],
                "value": self.password,
            },
            {
                "name": "Click on 'Log In' button",
                "type": "click",
                "selector": selectors["LOGIN_BUTTON"],
            }
        ]

        result = self.helper.execute_actions(login_type_1_actions)
        if not result or result.get("success", False) is False:
            print("Login type 1 failed")
            return False

        # Check for password error
        if self.helper.check_element_exists(selectors["PASSWORD_ERROR"]):
            print("Login type 1 failed: Incorrect password")
            return False
        print("Password error not found")
        
        # Check for error message
        if self.helper.check_element_exists(selectors["ERROR_MESSAGE"]):
            print("Login type 1 failed: Incorrect username or password")
            return False
        print("Error message not found")
        
        print("Login type 1 succeeded")
        return True
        

    def _login(self):
        print("Logging in to Instagram...")

        open_home_page_actions = [
            {
                "name": "Go to Instagram home page",
                "type": "goto",
                "url": HOME_PAGE_URL,
            },
            {
                "name": "Wait for load",
                "type": "wait_network",
                "timeout": 10000,
                "continue_on_failure": True,
            }
        ]

        # Open home page
        result = self.helper.execute_actions(open_home_page_actions)
        if not result or result.get("success", False) is False:
            print("Failed to open home page")
            return False
        
        # Check login type
        if self.helper.check_element_exists(SELECTORS["LOGIN"]["TYPE_1"]["USERNAME_FIELD"]):
            return self._login_type_1()
        
        print("Login failed: Unknown login type")
        return False

    # =============================
    # Complete 2FA methods
    # =============================
    
    def _complete_2fa_type_1(self):
        print("Using 2FA type 1...")
        selectors = SELECTORS["COMPLETE_2FA"]["TYPE_1"]

        complete_2fa_type_1_actions = [
            {
                "name": "Fill 2FA code",
                "type": "fill",
                "selector": selectors["CODE_FIELD"],
                "value": get_2fa_code(self.two_factor_code),
            },
            {
                "name": "Click on 'Confirm' button",
                "type": "click",
                "selector": selectors["CONFIRM_BUTTON"],
            }
        ]

        result = self.helper.execute_actions(complete_2fa_type_1_actions)
        if not result or result.get("success", False) is False:
            print("2FA type 1 failed")
            return False

        print("2FA type 1 succeeded")
        return True
    

    def _complete_2fa(self):
        print("Completing 2FA...")
        selectors = SELECTORS["COMPLETE_2FA"]

        if self.helper.check_element_exists(selectors["TYPE_1"]["CODE_FIELD"]):
            return self._complete_2fa_type_1()

        print("2FA failed: Unknown 2FA type")
        return False

    # =============================
    # Watch Reels methods
    # =============================
    # https://www.instagram.com/reels/DUczrnlDVDg

    def _open_reels_page(self):
        print("Opening Reels page...")
        
        open_reels_actions = [
            {
                "name": "Go to Reels page",
                "type": "goto",
                "url": REELS_PAGE_URL,
            },
            {
                "name": "Wait for load",
                "type": "wait_network",
                "timeout": 10000,
                "continue_on_failure": True,
            }
        ]

        result = self.helper.execute_actions(open_reels_actions)
        if not result or result.get("success", False) is False:
            print("Failed to open Reels page")
            return False

        print("Reels page opened successfully")
        return True
    

    def _mark_reel_as_watched(self):
        print("Marking reel as watched...")

        for attempt in range(MAX_ATTEMPTS_TO_MARK_REEL_AS_WATCHED):
            print(f"Attempt {attempt + 1} to mark reel as watched")
            current_url = self.helper.get_current_url()
            if search(r"https://www.instagram.com/reels/[\w-]+", current_url):
                reel_id = search(r"https://www.instagram.com/reels/([\w-]+)", current_url).group(1)
                if reel_id:
                    print(f"Reel '{reel_id}' marked as watched successfully")
                    return True
        
        print("Failed to mark reel as watched")
        return False

    
    def _do_reel_actions(
        self,
        reel_number: int,
        like: bool = False,
        unlike: bool = False,
        save: bool = False,
        unsave: bool = False,
        repost: bool = False,
        follow: bool = False,
        unfollow: bool = False,
    ):
        print("Doing reel actions...")
        selectors = SELECTORS["REEL_ACTIONS"]

        reel_actions = [
            {
                "name": "Click on Like button",
                "type": "click",
                "selector": selectors["LIKE_BUTTON"].format(reel_number=reel_number),
                "should_run": lambda: like,
            },
            {
                "name": "Click on Unlike button",
                "type": "click",
                "selector": selectors["UNLIKE_BUTTON"].format(reel_number=reel_number),
                "should_run": lambda: unlike,
            },
            {
                "name": "Click on Save button",
                "type": "click",
                "selector": selectors["SAVE_BUTTON"].format(reel_number=reel_number),
                "should_run": lambda: save,
            },
            {
                "name": "Click on Unsave button",
                "type": "click",
                "selector": selectors["UNSAVE_BUTTON"].format(reel_number=reel_number),
                "should_run": lambda: unsave,
            },
            {
                "name": "Click on Repost button",
                "type": "click",
                "selector": selectors["REPOST_BUTTON"].format(reel_number=reel_number),
                "should_run": lambda: repost,
            },
            {
                "name": "Click on Follow button",
                "type": "click",
                "selector": selectors["FOLLOW_BUTTON"].format(reel_number=reel_number),
                "should_run": lambda: follow,
            },
            {
                "name": "Click on Unfollow button",
                "type": "click",
                "selector": selectors["UNFOLLOW_BUTTON"].format(reel_number=reel_number),
                "should_run": lambda: unfollow,
            },
        ]

        result = self.helper.execute_actions(reel_actions)
        if not result or result.get("success", False) is False:
            print("Reel actions failed")
            return False

        print("Reel actions succeeded")
        return True


    def _watch_reels(self):
        print("Watching Reels...")
        
        # Open Reels page
        if not self._open_reels_page():
            self._take_screenshot()
            return False
        
        self._take_screenshot()
        
        # Switch between reels (using ArrowDown)
        for reel_number in range(NUMBER_OF_REELS_TO_WATCH):
            self._take_screenshot()

            # Watch the current reel (after reel page opened a random reel played)
            print(f"Watching reel {reel_number + 1}")
            self.helper.wait_natural_delay(15, 30)

            self._take_screenshot()

            # Mark reel as watched
            self._mark_reel_as_watched()

            # Do random reel actions
            do_like, do_save, do_repost, do_follow = bool(randint(0, 1)), bool(randint(0, 1)), bool(randint(0, 1)), bool(randint(0, 1))
            print(f"Doing reel actions | Like: {do_like}, Save: {do_save}, Repost: {do_repost}, Follow: {do_follow}")
            if do_like or do_save or do_repost or do_follow:
                self._do_reel_actions(like=do_like, save=do_save, repost=do_repost, follow=do_follow, reel_number=reel_number + 1)
                self._take_screenshot()

            # Press ArrowDown to switch to the next reel if it's not the last reel
            if reel_number < NUMBER_OF_REELS_TO_WATCH - 1:
                if self.helper.press_key("ArrowDown"):
                    print("Press ArrowDown succeeded")
                else:
                    print("Press ArrowDown failed")

        
        print("Watching Reels completed successfully")
        return True

    # =============================
    # Logout methods
    # =============================

    def _logout(self):
        print("Logging out...")
        selectors = SELECTORS["LOGOUT"]

        logout_actions = [
            {
                "name": "Click on Settings button",
                "type": "click",
                "selector": selectors["SETTINGS_BUTTON"],
            },
            {
                "name": "Click on Log out button",
                "type": "click",
                "selector": selectors["LOGOUT_BUTTON"],
            }
        ]

        result = self.helper.execute_actions(logout_actions)
        if not result or result.get("success", False) is False:
            print("Logout failed")
            return False

        print("Logout succeeded")
        return True

    # =============================
    # Main method
    # =============================

    def run(self):
        with sync_playwright() as p:
            try:
                indicators = SELECTORS["INDICATORS"]
                # Launch browser
                self.browser = p.chromium.launch(
                    headless=HEADLESS,
                    args=ARGS,
                    executable_path=BROWSER_PATH,
                )

                # Open new page
                self.page = self.browser.new_page(
                    viewport=VIEWPORT,
                )

                # Initialize helper
                self.helper = PlaywrightHelper(
                    page=self.page,
                    enable_logging=True,
                    log_prefix="[Instagram]",
                    natural_delay_min=2,
                    natural_delay_max=4
                )
                self._take_screenshot()

                # --------------------------
                # Login process
                # --------------------------

                # Login
                if not self._login():
                    self._take_screenshot()
                    return False

                self._take_screenshot()
                
                # Complete 2FA
                if not self._complete_2fa():
                    self._take_screenshot()
                    return False

                self._take_screenshot()

                # Check login indicator exists
                if not self.helper.check_element_exists(indicators["SUCCESS_LOGIN"]):
                    print("Login indicator not found")
                    self._take_screenshot()
                    return False
                else:
                    self._take_screenshot()
                    print("Login indicator found")
                
                # --------------------------
                # Watch Reels
                # --------------------------

                if not self._watch_reels():
                    self._take_screenshot()
                    return False

                self._take_screenshot()

                # --------------------------
                # Logout process
                # --------------------------

                # Skip logout confirmation in CI environment
                if not IS_CI:
                    input("Press Enter to continue with logout...")

                # Logout
                if not self._logout():
                    self._take_screenshot()
                    return False
                
                self._take_screenshot()
                
                # Check logout indicator exists
                if not self.helper.check_element_exists(indicators["SUCCESS_LOGOUT"]):
                    print("Logout indicator not found")
                    self._take_screenshot()
                    return False
                else:
                    self._take_screenshot()
                    print("Logout indicator found")

                self._take_screenshot()
                
                # Run completed successfully
                print("Run completed successfully")
                return True
            
            except Exception as e:
                print(f"An error occurred: {e}")
                return False

            finally:
                # Close browser
                if self.browser:
                    if ASK_BEFORE_CLOSE_BROWSER and not IS_CI:
                        input("Press Enter to close the browser...")
                    self.browser.close()
                    self.browser = None


if __name__ == "__main__":
    # Replace with your Instagram credentials
    username = getenv("INSTAGRAM_USERNAME")
    password = getenv("INSTAGRAM_PASSWORD")
    two_factor_code = getenv("INSTAGRAM_2FA_CODE")

    # Create an instance of Instagram
    instagram = Instagram(username, password, two_factor_code)

    # Run the script
    instagram.run()
