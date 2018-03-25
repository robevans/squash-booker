import time
from datetime import datetime, timedelta

from bs4 import BeautifulSoup
from twill import get_browser


class CourtUnavailableException(Exception):
    pass


class NoBookingSheetException(Exception):
    pass


class SquashBooker(object):
    def __init__(self, username, password, run_main=False):
        self._username = username
        self._password = password
        self._browser = get_browser()
        self._log_in()
        if run_main:
            self.run()

    def _log_in(self):
        self._browser.go('https://blackheathsquashclub.mycourts.co.uk')
        if self._browser.find_link("Logout"):
            print "Already logged in!"
        else:
            print "Logging in as {}".format(self._username)
            login_form = self._browser.get_form("1")
            username_field = self._browser.get_form_field(login_form, "username")
            password_field = self._browser.get_form_field(login_form, "password")
            username_field.value = self._username
            password_field.value = self._password
            self._browser.submit()
            if "denied" in self._browser.get_html().lower():
                raise Exception("Login failed!")

    def book(self, target_datetime):
        self._log_in()
        date_str = target_datetime.strftime('%d/%m/%Y')
        time_str = target_datetime.strftime('%H%M')
        print "Navigating to booking sheet"
        self._browser.go('https://blackheathsquashclub.mycourts.co.uk/bookings.asp')
        booking_sheet_link = self._browser.find_link(date_str)
        if not booking_sheet_link:
            raise NoBookingSheetException("Could not find booking sheet for {}!".format(date_str))
        self._browser.follow_link(booking_sheet_link)

        print "Attempting to book court at {} on {}".format(time_str, date_str)
        soup = BeautifulSoup(self._browser.get_html(), 'html.parser')
        booking_link = None
        for div in soup.findAll("div", {"class": "court_available"}):
            if div.getText().startswith(time_str):
                booking_url = div.find("a", {"class": "book_this_court"})['href'].replace(' ', '%20')
                booking_link = self._browser.find_link(booking_url.split('?')[1])

        if booking_link:
            self._browser.follow_link(booking_link)
            self._browser.follow_link(self._browser.find_link("Yes"))
            print "Booked {} {}".format(date_str, time_str)
        else:
            raise CourtUnavailableException(target_datetime)

    def _get_booking_table_rows(self):
        self._log_in()
        self._browser.go('https://blackheathsquashclub.mycourts.co.uk/my_bookings.asp')
        soup = BeautifulSoup(self._browser.get_html(), 'html.parser')
        bookings_table = soup.find("table", {"id": "my_bookings"})
        rows = bookings_table.findAll("tr")
        return rows

    def cancel(self, target_datetime):
        rows = self._get_booking_table_rows()

        target_str = target_datetime.strftime('%A %d %B %Y, %H%M hrs')
        matching_rows = [r for r in rows if target_str in str(r)]

        if not matching_rows:
            print "No cancel links found for {}".format(target_str)

        for r in matching_rows:
            cancel_link = r.find("a", text="cancel")["href"]
            self._browser.go(cancel_link)
            print "Cancelled {}".format(target_str)

    def cancel_date_if_no_opponents(self, cancel_date=datetime.today() + timedelta(days=1)):
        print "Cancelling courts without opponents on {}".format(cancel_date.strftime('%A %d %B %Y'))
        rows = self._get_booking_table_rows()
        rows_without_opponents_for_cancel_date = [r for r in rows
                                                  if 'select opponent(s)' in str(r)
                                                  and cancel_date.strftime('%A %d %B %Y') in str(r)]
        for r in rows_without_opponents_for_cancel_date:
            try:
                cancel_link = r.find("a", text="cancel")["href"]
                self._browser.go(cancel_link)
                print "Cancelled {}".format(str(r).split("subject=")[1].split('"')[0])
            except Exception, e:
                print "Failed to cancel court {} {}".format(e, r)

        if not rows_without_opponents_for_cancel_date:
            print "No courts to cancel"

    def try_book_with_timeout(self, target_date=(datetime.now() + timedelta(days=14)).date(),
                              target_time=datetime.strptime('1840', '%H%M').time(),
                              timeout=timedelta(minutes=5),
                              interval=timedelta(seconds=1)):
        target_datetime = datetime.combine(target_date, target_time)
        print "Trying to book {}".format(target_datetime.strftime('%A %d %B %Y, %H%M hrs'))
        start = datetime.now()
        while True:
            try:
                self.book(target_datetime)
                break
            except NoBookingSheetException, e:
                print e.message
                if datetime.now() > start + timeout:
                    print "Out of time, gave up at {}".format(datetime.now())
                    break
                time.sleep(interval.seconds)
            except CourtUnavailableException, e:
                print "Someone got there first", e.message

    def run(self):
        self.cancel_date_if_no_opponents()
        self.cancel_date_if_no_opponents(cancel_date=datetime.today() + timedelta(days=2))
        if datetime.today().weekday() in [0, 1]:
            self.try_book_with_timeout()


if __name__ == '__main__':
    # Update this part
    USERNAME = "...."
    PASSWORD = "...."

    booker = SquashBooker(USERNAME, PASSWORD, True)
