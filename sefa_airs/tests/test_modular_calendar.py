from datetime import date
import unittest
from modular_calendar import build_rule, generate_calendar

class CalendarTests(unittest.TestCase):
    def test_day_ten(self):
        c=generate_calendar('2026-11-02','morning',10)
        self.assertEqual((c['teaching_days'],c['total_scheduled_days']), (15,17))
        self.assertEqual(c['days'][10]['activity'],'cat')
        self.assertEqual(c['days'][-1]['activity'],'exam')
        self.assertEqual(c['planned_teaching_hours'],45)
    def test_evening_extra(self):
        c=generate_calendar('2026-11-02','evening',15)
        self.assertEqual((c['teaching_days'],c['total_scheduled_days']), (16,18))
        self.assertEqual(c['days'][11]['activity'],'cat')
    def test_weekend_hours(self):
        c=generate_calendar('2026-11-07','weekend',15,break_minutes=30)
        self.assertEqual(c['planned_teaching_hours'],105)
        self.assertEqual(c['days'][0]['date'],'2026-11-07')
    def test_invalid(self):
        with self.assertRaises(ValueError):build_rule('night',10)

if __name__=='__main__': unittest.main()

class FlexibleCalendarTests(unittest.TestCase):
    def test_custom_teaching_days(self):
        c=generate_calendar('2026-11-02','morning',10,before_cat=8,after_cat=6)
        self.assertEqual((c['teaching_days'],c['total_scheduled_days'],c['cat_day_number']),(14,16,9))
    def test_evening_extra_after_cat(self):
        c=generate_calendar('2026-11-02','evening',10,extra_days_before_cat=0)
        self.assertEqual(c['cat_day_number'],11)
        self.assertEqual(c['teaching_days'],16)
    def test_holiday_and_custom_hours(self):
        c=generate_calendar('2026-11-02','morning',10,excluded_dates=['2026-11-02'],start_time='09:00',end_time='12:00',break_minutes=30)
        self.assertEqual(c['days'][0]['date'],'2026-11-03')
        self.assertEqual(c['planned_teaching_hours'],37.5)
    def test_weekend_custom_days(self):
        c=generate_calendar('2026-11-07','weekend',15,weekdays=[5],coverage_target=90)
        self.assertTrue(all(date.fromisoformat(r['date']).weekday()==5 for r in c['days']))
        self.assertEqual(c['planned_hours_at_target'],101.25)
    def test_impossible_horizon(self):
        with self.assertRaises(ValueError):
            generate_calendar('2026-11-07','weekend',10,weekdays=[6],max_calendar_days=10)
