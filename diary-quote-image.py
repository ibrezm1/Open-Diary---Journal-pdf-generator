import os
import time
import calendar
import datetime
import requests
import textwrap
import json
from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
from reportlab.lib.units import cm
from dotenv import load_dotenv
import openai

# Load environment variables
load_dotenv()

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
    def __init__(self, year, filename):
        self.year = year
        self.filename = filename
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
        image_obj = self.content_gen.get_month_image(month_name)
        inspiration_text = self.content_gen.get_month_inspiration(month_name, self.year)

        # 2. Draw Month Title
        self.c.setFont("Courier-BoldOblique", 40)  # Changed to a cursive-like font
        self.c.drawCentredString(self.width/2, self.height - 4*cm, month_name.upper())

        # 3. Draw Image
        if image_obj:
            img_w = 16 * cm
            img_h = 12 * cm
            img_x = (self.width - img_w) / 2
            img_y = self.height - 18 * cm
            self.c.drawImage(image_obj, img_x, img_y, width=img_w, height=img_h)

            # Draw a border around the image
            self.c.setStrokeColor(colors.black)
            self.c.setLineWidth(2)
            self.c.rect(img_x, img_y, img_w, img_h)

        # 4. Draw Inspiration Text
        text_y = self.height - 21 * cm
        self.c.setFont("Helvetica-Oblique", 12)
        self.c.setFillColor(colors.darkgrey)

        lines = self.wrap_text(inspiration_text, self.width - 6*cm, font_size=12)
        for line in lines:
            self.c.drawCentredString(self.width/2, text_y, line)
            text_y -= 0.6 * cm

        self.c.setFillColor(colors.black)
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
        grid_top = self.height - 6 * cm
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

    def generate(self):
        print(f"Generating Diary for {self.year}...")
        
        # 0. Vision Board
        self.draw_header("2025 Vision Board")
        self.draw_vision_board_grid()
        self.c.showPage()
        
        # Quotes
        quotes = QuoteFetcher().fetch_quotes(370)
        q_idx = 0
        
        for month in range(1, 13):
            # 1. Month Intro (Image + AI Text)
            self.create_month_intro_page(month)
            
            # 2. Monthly Planner
            self.create_monthly_planner(month)
            
            # 3. Daily Pages
            days = calendar.monthrange(self.year, month)[1]
            for day in range(1, days + 1):
                q = quotes[q_idx % len(quotes)]
                q_idx += 1
                self.create_daily_page(datetime.date(self.year, month, day), q)
                
            # 4. End of Month Review
            self.create_monthly_achievement(month)
            
        self.c.save()
        print(f"Done! Saved as {self.filename}")

if __name__ == "__main__":
    DiaryGenerator(2025, "2025_Smart_Diary.pdf").generate()