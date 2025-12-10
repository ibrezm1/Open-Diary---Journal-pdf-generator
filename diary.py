from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.units import cm
import calendar
import datetime
import requests
import time
import textwrap

class QuoteFetcher:
    def __init__(self):
        self.api_url = "https://zenquotes.io/api/quotes"
        self.quotes = []

    def fetch_quotes(self, count=400):
        """
        Fetches quotes in batches of 50 to respect API guidelines.
        We need about 366 quotes for a full year.
        """
        print("Fetching quotes from ZenQuotes... this may take a moment...")
        while len(self.quotes) < count:
            try:
                response = requests.get(self.api_url)
                if response.status_code == 200:
                    data = response.json()
                    for item in data:
                        # item format: {'q': 'quote text', 'a': 'author name', ...}
                        q_text = item.get('q')
                        q_author = item.get('a')
                        self.quotes.append((q_text, q_author))
                    
                    # Remove duplicates just in case
                    self.quotes = list(set(self.quotes))
                    print(f"Collected {len(self.quotes)} quotes...")
                else:
                    print("Error fetching quotes. Using placeholders.")
                    break
                
                # Sleep to respect rate limits (limit is usually 5 req per 30s for free tier)
                if len(self.quotes) < count:
                    time.sleep(6) 
            except Exception as e:
                print(f"Connection error: {e}")
                break
        
        # If we failed to get enough, fill with generic text
        while len(self.quotes) < count:
            self.quotes.append(("Your time is limited, so don't waste it living someone else's life.", "Steve Jobs"))
            
        return self.quotes

class DiaryGenerator:
    def __init__(self, year, filename):
        self.year = year
        self.filename = filename
        self.c = canvas.Canvas(filename, pagesize=A4)
        self.width, self.height = A4
        self.margin = 1.5 * cm
        
        # Colors
        self.line_color = colors.grey
        self.text_color = colors.black
        self.faint_line = colors.lightgrey

    def draw_header(self, title, subtitle=""):
        self.c.setFont("Helvetica-Bold", 24)
        self.c.drawCentredString(self.width / 2, self.height - 2.5 * cm, title)
        if subtitle:
            self.c.setFont("Helvetica", 10)
            self.c.drawCentredString(self.width / 2, self.height - 3.5 * cm, subtitle)

    def wrap_text(self, text, max_width, font="Helvetica", size=10):
        """Helper to wrap text for the PDF canvas"""
        # Simple character count estimation or reportlab's stringWidth could be used
        # Here using textwrap for simplicity
        char_limit = int(max_width / (size * 0.5)) # Approximate char limit
        return textwrap.wrap(text, width=char_limit)

    def create_annual_vision_board(self):
        self.draw_header("Vision Board")
        
        # Instruction text
        text = ("Use this space to paint, doodle or cut pictures out of magazines. "
                "The goal is to create a powerful visualization tool to aid in manifesting "
                "your dreams. Bring your {} goals to life.".format(self.year))
        
        self.c.setFont("Helvetica-Oblique", 10)
        self.c.setFillColor(colors.darkgrey)
        
        lines = self.wrap_text(text, self.width - 2*self.margin)
        text_y = self.height - 3.5*cm
        for line in lines:
            self.c.drawCentredString(self.width/2, text_y, line)
            text_y -= 14
        
        self.c.setFillColor(colors.black)

        # Draw Grid
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
                
        self.c.showPage()

    def create_monthly_planner(self, month):
        month_name = calendar.month_name[month]
        self.draw_header(f"{month_name} {self.year}")
        
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

        note_y = y - 1 * cm
        self.c.setFont("Helvetica-Bold", 12)
        self.c.drawString(self.margin, note_y, "Monthly Vision & Goals:")
        
        self.c.setStrokeColor(self.faint_line)
        while note_y > self.margin:
            note_y -= 0.8 * cm
            self.c.line(self.margin, note_y, self.width - self.margin, note_y)
            
        self.c.showPage()

    def create_daily_page(self, date_obj, quote_data):
        quote, author = quote_data
        
        # --- Top Quote Section ---
        self.c.setFont("Helvetica-Oblique", 9)
        self.c.setFillColor(colors.darkgrey)
        
        # Simple wrapping for long quotes
        quote_y = self.height - 1.2 * cm
        wrapped_quote = self.wrap_text(f'"{quote}"', self.width - 4*self.margin, size=9)
        
        for line in wrapped_quote:
            self.c.drawCentredString(self.width/2, quote_y, line)
            quote_y -= 10
        self.c.setFont("Helvetica-Bold", 9)
        self.c.drawCentredString(self.width/2, quote_y, f"- {author}")

        # --- Header ---
        self.c.setFillColor(colors.black)
        day_str = date_obj.strftime("%A")
        date_full = date_obj.strftime("%d %B %Y")
        
        self.c.setFont("Helvetica-Bold", 18)
        # Shift header down slightly to accommodate quote
        header_y = self.height - 3 * cm 
        self.c.drawString(self.margin, header_y, f"{day_str} | {date_full}")
        
        self.c.setStrokeColor(colors.black)
        self.c.setLineWidth(1)
        self.c.line(self.margin, header_y - 0.5*cm, self.width - self.margin, header_y - 0.5*cm)

        # Layout
        left_col_width = (self.width - 2 * self.margin) * 0.45
        right_col_x = self.margin + left_col_width + 0.5*cm
        right_col_width = (self.width - 2 * self.margin) * 0.55 - 0.5*cm
        start_y = header_y - 1.5 * cm
        
        # --- LEFT COLUMN: Schedule ---
        self.c.setFont("Helvetica", 9)
        current_y = start_y
        line_height = 0.8 * cm 
        
        for hour in range(6, 24):
            time_str = f"{hour:02d}:00"
            self.c.drawString(self.margin, current_y, time_str)
            self.c.setStrokeColor(self.faint_line)
            self.c.line(self.margin + 1.2*cm, current_y - 2, self.margin + left_col_width, current_y - 2)
            current_y -= line_height

        # Notes Box
        self.c.setFont("Helvetica-Bold", 10)
        self.c.setFillColor(colors.black)
        self.c.drawString(self.margin, current_y - 1*cm, "Notes")
        rect_bottom = self.margin
        rect_height = (current_y - 1.5*cm) - rect_bottom
        self.c.setStrokeColor(colors.grey)
        self.c.rect(self.margin, rect_bottom, self.width - 2*self.margin, rect_height)

        # --- RIGHT COLUMN: Prompts ---
        prompts = [
            ("Today's quick wins", 3),
            ("Health and nutrition", 3),
            ("Today, I am grateful for...", 3),
            ("Today's self care", 2),
            ("Chart your cycle", 2),
            ("Positive affirmation", 2)
        ]
        
        r_y = start_y + 0.5*cm
        
        for title, lines in prompts:
            box_height = lines * 0.9 * cm
            r_y -= box_height
            
            self.c.setFont("Helvetica", 9)
            self.c.setFillColor(colors.darkgrey)
            self.c.drawString(right_col_x, r_y + box_height - 10, title)
            
            self.c.setStrokeColor(self.faint_line)
            for i in range(1, lines + 1):
                ly = (r_y + box_height) - (i * 0.8 * cm)
                if i == lines:
                     self.c.setStrokeColor(colors.grey)
                     self.c.line(right_col_x, r_y, right_col_x + right_col_width, r_y)
                else:
                     self.c.setStrokeColor(self.faint_line)
                     self.c.line(right_col_x, ly, right_col_x + right_col_width, ly)

            r_y -= 0.2 * cm 

        self.c.showPage()

    def create_monthly_achievement_page(self, month):
        month_name = calendar.month_name[month]
        self.draw_header(f"{month_name} Review", "Celebrate your wins and reflect on your growth")
        
        start_y = self.height - 4 * cm
        
        # Sections for review
        sections = [
            ("Biggest Achievement this month", 4),
            ("What I learned", 4),
            ("Things to improve next month", 4),
            ("Memorable Moments", 4),
            ("How did I feel overall? (Circle one)", 0) # 0 lines means custom handling
        ]
        
        current_y = start_y
        
        for title, lines in sections:
            self.c.setFont("Helvetica-Bold", 12)
            self.c.setFillColor(colors.black)
            self.c.drawString(self.margin, current_y, title)
            current_y -= 0.8 * cm
            
            if lines > 0:
                self.c.setStrokeColor(self.faint_line)
                for _ in range(lines):
                    self.c.line(self.margin, current_y, self.width - self.margin, current_y)
                    current_y -= 0.9 * cm
                current_y -= 1 * cm # Spacer
            else:
                # Custom handling for mood/feeling
                moods = ["Energized", "Content", "Stressed", "Productive", "Tired", "Inspired"]
                mood_x = self.margin
                self.c.setFont("Helvetica", 11)
                for mood in moods:
                    self.c.drawString(mood_x, current_y, mood)
                    mood_x += 3 * cm
                current_y -= 2 * cm

        # Rating Box
        self.c.setFont("Helvetica-Bold", 12)
        self.c.drawString(self.margin, current_y, "Rate this month (1-10):")
        self.c.rect(self.margin + 5*cm, current_y - 0.2*cm, 1.5*cm, 1.5*cm)
        
        self.c.showPage()

    def generate(self):
        # 1. Fetch Quotes
        fetcher = QuoteFetcher()
        quotes_list = fetcher.fetch_quotes(count=370)
        quote_index = 0

        print(f"Generating diary for {self.year}...")
        
        # 2. Annual Vision Board
        self.create_annual_vision_board()
        
        # Iterate through months
        for month in range(1, 13):
            # 3. Monthly Planner
            self.create_monthly_planner(month)
            
            # 4. Daily Pages
            num_days = calendar.monthrange(self.year, month)[1]
            for day in range(1, num_days + 1):
                date_obj = datetime.date(self.year, month, day)
                
                # Get a quote (cycle if we run out)
                current_quote = quotes_list[quote_index % len(quotes_list)]
                quote_index += 1
                
                self.create_daily_page(date_obj, current_quote)
            
            # 5. Monthly Achievement Page
            self.create_monthly_achievement_page(month)
                
        self.c.save()
        print(f"Saved as {self.filename}")

if __name__ == "__main__":
    my_diary = DiaryGenerator(2025, "2025_Planner_Diary_With_Quotes.pdf")
    my_diary.generate()