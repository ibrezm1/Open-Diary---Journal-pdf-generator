import os
import io
import time
import calendar
import datetime
import requests
import textwrap
import json
from reportlab.lib.colors import HexColor
from io import BytesIO
from PIL import Image, ImageOps
from reportlab.lib.utils import ImageReader  # <--- Make sure you import this
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
from reportlab.lib.units import cm
from dotenv import load_dotenv
import openai

# Load environment variables
load_dotenv()


def add_bw_museum_frame(image_input):
    """
    Robustly handles input (ImageReader, Path, Bytes, or Image) 
    and returns a B&W Framed PIL Image.
    """
    img = None

    # 1. Normalize Input to a PIL Image
    if isinstance(image_input, ImageReader):
        # Extract the hidden PIL image from the ReportLab wrapper
        if hasattr(image_input, '_image'):
            img = image_input._image.copy() # Copy it to avoid modifying the original
        else:
            # Fallback for rare cases where ImageReader holds raw data
            img = Image.open(io.BytesIO(image_input.getJPEGData()))

    elif isinstance(image_input, str):
        img = Image.open(image_input)
        
    elif isinstance(image_input, bytes):
        img = Image.open(io.BytesIO(image_input))
        
    elif hasattr(image_input, 'read'):
        img = Image.open(image_input)
        
    elif isinstance(image_input, Image.Image):
        img = image_input
        
    else:
        raise ValueError(f"Unknown image input type: {type(image_input)}")

    # 2. Convert to Grayscale (B&W)
    img = img.convert("L") 
    img = img.convert("RGB") # Convert back to RGB for border coloring

    # 3. Create the Frame
    # Inner definition line
    img = ImageOps.expand(img, border=2, fill="black")
    # Wide White Mat
    img = ImageOps.expand(img, border=3, fill="white")
    # Separator line
    img = ImageOps.expand(img, border=1, fill="#333333")
    # Outer Black Frame
    img = ImageOps.expand(img, border=3, fill="black")

    return img

class ContentGenerator:
    def __init__(self):
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            print("WARNING: OPENROUTER_API_KEY not found in .env file. AI text will be disabled.")

    def get_month_inspiration(self, month_name, year):
        """Uses OpenRouter to generate an inspirational intro for the month."""
        if not self.api_key:
            return f"Welcome to {month_name}. Make it count!"

        prompt = (f"Write a short, poetic, and inspiring paragraph (approx 60-80 words) "
                  f"about the month of {month_name} {year}. "
                  f"Focus on the feeling of the season, new beginnings, or productivity. "
                  f"Do not use hashtags.")

        try:
            response = requests.post(
                url="https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "HTTP-Referer": "https://your-site-url.com",  # Optional
                    "X-Title": "Your Site Name"  # Optional
                },
                data=json.dumps({
                    "model": "mistralai/mistral-7b-instruct:free",
                    "messages": [
                        {"role": "user", "content": prompt}
                    ]
                })
            )

            if response.status_code == 200:
                result = response.json()
                # remove "<s>" and "</s>" if present
                return result['choices'][0]['message']['content'].strip().replace("<s>", "").replace("</s>", "")
            else:
                print(f"OpenRouter Error: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"OpenRouter Exception: {e}")

        return f"Welcome to {month_name}. A new month, a new beginning."

    def get_month_image(self, month_name):
        """
        Fetches a random grayscale image relevant to the month/season.
        Uses loremflickr (free, no key required) with the /g/ (grayscale) tag.
        """
        # Map months to search keywords
        season_keywords = {
            "January": "winter,snow,cozy", "February": "winter,love,mist",
            "March": "spring,sprout,green", "April": "rain,flowers,bloom",
            "May": "nature,sun,garden", "June": "summer,beach,sunshine",
            "July": "summer,adventure,sky", "August": "summer,heat,sunset",
            "September": "autumn,leaves,school", "October": "autumn,pumpkin,forest",
            "November": "autumn,frost,coffee", "December": "winter,lights,celebration"
        }
        
        keyword = season_keywords.get(month_name, "nature")
        # URL structure: https://loremflickr.com/g/{width}/{height}/{keywords}/all
        # /g/ ensures it is black and white (grayscale)
        url = f"https://loremflickr.com/g/800/600/{keyword}/all"
        
        print(f"Downloading image for {month_name} ({keyword})...")
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                img_data = BytesIO(response.content)
                return ImageReader(img_data)
        except Exception as e:
            print(f"Image download error: {e}")
        return None

class QuoteFetcher:
    def __init__(self, cache_file="quotes_cache.json"):
        self.api_url = "https://zenquotes.io/api/quotes"
        self.cache_file = cache_file
        self.quotes = self.load_cached_quotes()

    def load_cached_quotes(self):
        """Load quotes from the cache file if it exists."""
        try:
            with open(self.cache_file, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return []

    def save_quotes_to_cache(self):
        """Save the current quotes to the cache file."""
        with open(self.cache_file, "w") as f:
            json.dump(self.quotes, f)

    def fetch_quotes(self, count=400):
        """Fetch quotes from the API or use cached quotes."""
        print("Fetching quotes... (This creates a cache to save time)")
        if len(self.quotes) >= count:
            print("Using cached quotes.")
            return self.quotes[:count]

        # Fetch new quotes if cache is insufficient
        try:
            response = requests.get(self.api_url)
            if response.status_code == 200:
                data = response.json()
                for item in data:
                    self.quotes.append((item.get('q'), item.get('a')))
                # Remove duplicates
                self.quotes = list(set(self.quotes))
                self.save_quotes_to_cache()
        except Exception as e:
            print(f"Error fetching quotes: {e}")

        # Fill with placeholders if necessary
        while len(self.quotes) < count:
            self.quotes.append(("The secret of getting ahead is getting started.", "Mark Twain"))

        self.save_quotes_to_cache()
        return self.quotes[:count]


class DiaryGenerator:
    def __init__(self, year, filename, test_mode=False):
        self.year = year
        self.filename = filename
        self.test_mode = test_mode
        self.c = canvas.Canvas(filename, pagesize=A4)
        self.width, self.height = A4
        self.margin = 1.5 * cm
        self.content_gen = ContentGenerator()
        
        self.faint_line = colors.lightgrey

    def wrap_text(self, text, width, font_size=10):
        """Rough text wrapper"""
        char_limit = int(width / (font_size * 0.45))
        return textwrap.wrap(text, width=char_limit)

    def draw_header(self, title, subtitle=""):
        self.c.setFont("Helvetica-Bold", 24)
        self.c.drawCentredString(self.width / 2, self.height - 2.5 * cm, title)
        if subtitle:
            self.c.setFont("Helvetica", 12)
            self.c.drawCentredString(self.width / 2, self.height - 3.5 * cm, subtitle)

    # --- PAGE 1: Intro Page for the Month ---
    def create_month_intro_page(self, month):
        month_name = calendar.month_name[month]

        # 1. Get Content
        # (Assuming these return valid paths or objects)
        raw_image = self.content_gen.get_month_image(month_name)
        inspiration_text = self.content_gen.get_month_inspiration(month_name, self.year)

        # 2. Draw Month Title
        # Use 'ZapfChancery-MediumItalic' for a calligraphy look, or 'Times-Bold' for classic
        self.c.setFont("Times-Italic", 50) 
        self.c.setFillColor(colors.black)
        
        # Draw Title
        title_y = self.height - 4.5 * cm
        self.c.drawCentredString(self.width / 2, title_y, month_name)

        # Draw an elegant black separator line under title
        self.c.setStrokeColor(colors.black)
        self.c.setLineWidth(1.5)
        self.c.line((self.width/2)-2*cm, title_y - 15, (self.width/2)+2*cm, title_y - 15)

        # 3. Process and Draw Image (With Frame)
        if raw_image:
            # A. Generate the B&W framed image in memory
            framed_img = add_bw_museum_frame(raw_image)
            
            # B. Convert to ReportLab ImageReader
            img_obj = ImageReader(framed_img)

            # C. Calculate aspect ratio to fit page nicely
            # We want the image to be about 16cm wide maximum
            orig_w, orig_h = framed_img.size
            aspect = orig_h / float(orig_w)
            
            display_w = 16 * cm
            display_h = display_w * aspect
            
            # Center the image
            img_x = (self.width - display_w) / 2
            
            # Position it dynamically based on the title
            img_y = title_y - 2*cm - display_h 

            self.c.drawImage(img_obj, img_x, img_y, width=display_w, height=display_h)
        else:
            # Fallback if no image, just set Y cursor lower
            img_y = title_y - 5*cm

        # 4. Draw Inspiration Text
        # Use Times-Italic for a "Book Quote" feel
        self.c.setFont("Times-Italic", 14)
        self.c.setFillColor(colors.black) # Strictly black

        # Position text relative to the bottom of the image
        text_y = img_y - 2 * cm 

        # Add a decorative visual anchor (small line) before text
        self.c.setLineWidth(0.5)
        self.c.line((self.width/2)-1*cm, text_y + 1*cm, (self.width/2)+1*cm, text_y + 1*cm)

        lines = self.wrap_text(inspiration_text, self.width - 8*cm, font_size=14)
        for line in lines:
            self.c.drawCentredString(self.width/2, text_y, line)
            text_y -= 0.8 * cm

        self.c.showPage()
    def create_monthly_planner(self, month):
        month_name = calendar.month_name[month]
        self.draw_header(f"{month_name} Overview")
        
        # Grid Setup
        cal = calendar.monthcalendar(self.year, month)
        grid_x = self.margin
        grid_y = self.height - 5 * cm
        col_width = (self.width - 2 * self.margin) / 7
        row_height = 2.5 * cm
        
        days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        
        self.c.setFont("Helvetica-Bold", 10)
        for i, day in enumerate(days):
            self.c.drawCentredString(grid_x + (i * col_width) + (col_width/2), grid_y + 0.5*cm, day)
            
        self.c.setStrokeColor(colors.black)
        y = grid_y
        for week in cal:
            x = grid_x
            for day in week:
                self.c.rect(x, y - row_height, col_width, row_height)
                if day != 0:
                    self.c.setFont("Helvetica", 10)
                    self.c.drawString(x + 2, y - 12, str(day))
                x += col_width
            y -= row_height

        # Goals Section
        note_y = y - 1.5 * cm
        self.c.setFont("Helvetica-Bold", 12)
        self.c.drawString(self.margin, note_y, "Key Goals for the Month:")
        
        self.c.setStrokeColor(self.faint_line)
        while note_y > self.margin:
            note_y -= 0.8 * cm
            self.c.line(self.margin, note_y, self.width - self.margin, note_y)
            
        self.c.showPage()

    def create_daily_page(self, date_obj, quote_data):
        quote, author = quote_data

        # Quote
        self.c.setFont("Helvetica-Oblique", 9)
        self.c.setFillColor(colors.darkgrey)
        quote_y = self.height - 1.2 * cm
        wrapped = self.wrap_text(f'"{quote}"', self.width - 4*self.margin, 9)
        for line in wrapped:
            self.c.drawCentredString(self.width/2, quote_y, line)
            quote_y -= 10
        self.c.setFont("Helvetica-Bold", 9)
        
        # Change to right-align the author text
        self.c.drawRightString(self.width - self.margin, quote_y, f"- {author}")

        # Reduce spacing between author and date header
        header_y = quote_y - 1.5 * cm  # Adjusted spacing
        self.c.setFillColor(colors.black)
        self.c.setFont("Helvetica-Bold", 18)
        self.c.drawString(self.margin, header_y, f"{date_obj.strftime('%A')} | {date_obj.strftime('%d %B %Y')}")
        self.c.setStrokeColor(colors.black)
        self.c.line(self.margin, header_y - 10, self.width - self.margin, header_y - 10)

        # Columns
        start_y = header_y - 1.5 * cm
        left_w = (self.width - 2*self.margin) * 0.55  # Increased width for notes section
        right_x = self.margin + left_w + 0.5*cm
        
        # Schedule (Left)
        self.c.setFont("Helvetica", 9)
        curr_y = start_y
        for h in range(6, 24):
            self.c.drawString(self.margin, curr_y, f"{h:02d}:00")
            self.c.setStrokeColor(self.faint_line)
            self.c.line(self.margin + 1.2*cm, curr_y-2, self.margin+left_w, curr_y-2)
            curr_y -= 0.8*cm

        # Notes (full bottom centered)
        self.c.setFont("Helvetica-Bold", 10)
        self.c.setFillColor(colors.black)
        self.c.drawString(self.margin, curr_y - 1*cm, "Notes")
        rect_bottom = self.margin
        rect_height = (curr_y - 1.5*cm) - rect_bottom
        self.c.setStrokeColor(colors.grey)
        self.c.rect(self.margin, rect_bottom, self.width - 2*self.margin, rect_height)

        # Add horizontal lines to the full width of the Notes rectangle
        rect_width = self.width - 2 * self.margin
        right_edge = self.width - self.margin  # Calculate far right edge
        
        # Set color to a very pale grey (Lighter than standard colors.lightgrey)
        self.c.setStrokeColor(HexColor("#E0E0E0")) 
        self.c.setLineWidth(0.5)
        
        line_y = rect_bottom + rect_height - 0.8 * cm
        
        while line_y > rect_bottom + 0.3 * cm:
            # Draw from left margin to right margin
            # keep some space on the left and right for the notes
            self.c.line(self.margin + 0.5*cm, line_y, right_edge - 0.5*cm, line_y)
            line_y -= 0.8 * cm

        # Prompts (Right)
        prompts = [
            ("Today's quick wins", 3), ("Health & Nutrition", 3),
            ("Grateful for...", 3), ("Self Care", 2), 
            ("Cycle / Mood", 2), ("Affirmation", 2)
        ]
        r_y = start_y + 0.5*cm
        for title, count in prompts:
            h = count * 0.9 * cm
            r_y -= h
            self.c.setFont("Helvetica", 9)
            self.c.setFillColor(colors.darkgrey)
            self.c.drawString(right_x, r_y + h - 10, title)
            self.c.setStrokeColor(self.faint_line)
            for i in range(1, count+1):
                ly = (r_y + h) - (i * 0.8 * cm)
                if i == count: self.c.setStrokeColor(colors.grey)
                self.c.line(right_x, ly, self.width - self.margin, ly)
            r_y -= 0.2*cm

        self.c.showPage()

    def create_monthly_achievement(self, month):
        self.draw_header(f"{calendar.month_name[month]} Review")
        
        sections = ["Biggest Achievement", "What I Learned", "To Improve", "Memorable Moments"]
        y = self.height - 4.5 * cm
        for sec in sections:
            self.c.setFont("Helvetica-Bold", 12)
            self.c.drawString(self.margin, y, sec)
            y -= 0.6*cm
            self.c.setStrokeColor(self.faint_line)
            for _ in range(4):
                self.c.line(self.margin, y, self.width - self.margin, y)
                y -= 0.9*cm
            y -= 1*cm
            
        self.c.showPage()

    def draw_vision_board_grid(self):
        """Draws a grid for the vision board page."""
        grid_top = self.height - 3 * cm
        grid_bottom = self.margin
        grid_height = grid_top - grid_bottom
        grid_width = self.width - 2 * self.margin

        rows, cols = 4, 3
        box_w = grid_width / cols
        box_h = grid_height / rows

        self.c.setStrokeColor(colors.grey)
        self.c.setLineWidth(0.5)

        for r in range(rows):
            for col in range(cols):
                x = self.margin + (col * box_w)
                y = grid_bottom + (r * box_h)
                self.c.rect(x, y, box_w, box_h)

    def create_year_goals_page(self):
        """Creates a structured page for yearly goals."""
        self.draw_header("2025 Year Goals")

        # Define 4 main categories
        categories = [
            "Personal Growth & Skills",
            "Career & Business",
            "Health & Wellness",
            "Financial Freedom"
        ]

        # Layout calculations
        start_y = self.height - 4.5 * cm
        section_height = (start_y - self.margin) / 4
        
        current_y = start_y

        for category in categories:
            # 1. Draw Category Title
            # self.c.setFont("Helvetica", 9)
            self.c.setFont("Helvetica", 15)
            self.c.setFillColor(colors.black)
            self.c.drawString(self.margin, current_y, category)
            
            # 2. Draw Faint Writing Lines below the title
            # We fit about 5 lines per section
            line_start_y = current_y - 1.2 * cm
            line_spacing = 0.9 * cm
            
            self.c.setStrokeColor(HexColor("#E0E0E0")) # Very pale grey
            self.c.setLineWidth(0.5)

            for _ in range(4): # 4 lines per category
                self.c.line(self.margin, line_start_y, self.width - self.margin, line_start_y)
                line_start_y -= line_spacing

            # Move cursor down for next section
            current_y -= section_height

        self.c.showPage()

    def generate(self):
        if self.test_mode:
            print(f"*** TEST MODE ACTIVE ***")
            print(f"Generating TEST Diary for {self.year} (January only, Day 1 only)...")
        else:
            print(f"Generating Diary for {self.year}...")
        
        # 0. Vision Board
        self.draw_header("2025 Vision Board")
        self.draw_vision_board_grid()
        self.c.showPage()

        # 1. Year Goals
        self.create_year_goals_page()

        # Quotes
        quotes = QuoteFetcher().fetch_quotes(370)
        q_idx = 0
        
        # Determine which months to process
        if self.test_mode:
            months_to_process = [1]  # Only January
            print("Processing: January only")
        else:
            months_to_process = range(1, 13)  # All months
        
        for month in months_to_process:
            # 1. Month Intro (Image + AI Text)
            print(f"Creating intro page for {calendar.month_name[month]}...")
            self.create_month_intro_page(month)
            
            # 2. Monthly Planner
            print(f"Creating monthly planner for {calendar.month_name[month]}...")
            self.create_monthly_planner(month)
            
            # 3. Daily Pages
            days = calendar.monthrange(self.year, month)[1]
            
            # Determine which days to process
            if self.test_mode:
                days_to_process = [1]  # Only day 1
                print(f"Creating daily page for day 1 only...")
            else:
                days_to_process = range(1, days + 1)  # All days
            
            for day in days_to_process:
                q = quotes[q_idx % len(quotes)]
                q_idx += 1
                self.create_daily_page(datetime.date(self.year, month, day), q)
                
            # 4. End of Month Review
            print(f"Creating end-of-month review for {calendar.month_name[month]}...")
            self.create_monthly_achievement(month)
            
        self.c.save()
        if self.test_mode:
            print(f"*** TEST MODE COMPLETE ***")
        print(f"Done! Saved as {self.filename}")

if __name__ == "__main__":
    # Set test_mode=True to generate only January with day 1 (for testing)
    # Set test_mode=False to generate the full year diary
    DiaryGenerator(2025, "2025_Smart_Diary_TEST.pdf", test_mode=False).generate()