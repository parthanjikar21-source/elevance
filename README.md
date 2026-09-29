# Cineverse - Next-Generation Cinema Ticketing & Management Platform

A feature-rich, high-concurrency movie discovery, smart seat reservation, payment processing, and business analytics platform built with Django, ReportLab, Celery, and SQLite/PostgreSQL.

---

## 🔑 Demonstration Credentials

| Role | Username | Password | Permissions & Purpose |
| :--- | :--- | :--- | :--- |
| **System Administrator** | `admin` | `Admin@12345` | Full access to Admin Analytics Dashboard, Django Admin Portal (`/admin/`), and Gatekeeper Scanner (`/bookings/verify/<token>/`). |
| **Verified Viewer Patron** | `cinephile` | `User@12345` | Pre-loaded with past watched bookings (*Oppenheimer*, *Dune: Part Two*) to demonstrate the **Verified Viewer Badge**, review publishing, and review editing. |
| **Community Patron** | `priya_k` | `User@12345` | Standard user for testing concurrent seat reservation conflicts and reviews. |

---

## 🌟 Modules & Features Summary

### 1. Movie Management with Trailer, Reviews & Ratings
- **Admin Interface:** Full management of movies, genres, languages, cast members, theaters, screens, and schedules via standard Django Admin and custom interfaces.
- **Movie Specifications:** Secure YouTube trailer embed (using privacy-enhanced `youtube-nocookie.com`), multiple poster images, age certifications (`U`, `UA 7+`, `UA 13+`, `UA 16+`, `A`, `PG-13`, `R`), duration, and synopses.
- **Verified Viewer Badge & Reviews:** Only registered users who have actually booked and watched a movie (`show__show_date <= today`) can rate and review it.
- **Dynamic Rating Calculation:** Average rating and review counts are recalculated on database level upon review addition, edit, or deletion.
- **Moderation:** Community members can report inappropriate or spoiler content with reasons (`SPAM`, `OFFENSIVE`, `SPOILERS`, `INAPPROPRIATE`), which flags reviews for admin review.
- **Recommendations:** Movie detail pages display similar movies based on overlapping genres and languages, plus trending and recently released carousels.

### 2. Smart Seat Reservation with Live Availability
- **Interactive Visual Seat Matrix:** Screen curved graphic with status indicators for **Available** (emerald glow), **Selected by You** (emerald), **Temporary Hold** (amber with countdown), and **Booked** (muted dark).
- **Strict 2-Minute Temporary Lock:** Selected seats remain locked for 120 seconds. If checkout is not completed within 2 minutes, the system automatically releases them.
- **Race Condition & Concurrency Protection:** Built using Django atomic transactions (`transaction.atomic()`) and `select_for_update()` database locks. If multiple users attempt to reserve the same seats simultaneously, the conflicting attempt is rejected with HTTP 409 and clear user feedback.
- **Seat Selection Modification:** Users can cancel or modify seats before payment, releasing held seats immediately back to the pool.
- **Real-Time Polling:** Background polling endpoint (`/bookings/api/shows/<show_id>/availability/`) keeps open browser tabs synchronized.

### 3. Complete Payment Workflow & Booking Management
- **Payment Gateway Integration:** Integrated Razorpay and test simulation suites supporting:
  - Successful transactions
  - Failed payments (with automated seat release)
  - User-cancelled checkouts
  - Payment retries
  - Server-side cryptographic HMAC SHA256 signature verification
  - Server-side webhook receiver (`/payments/webhook/razorpay/`)
- **Strict Idempotency:** Duplicate payment confirmations or repeated webhook notifications never produce duplicate bookings or double ticket issuances.
- **Customer History:** Users can track complete payment transactions, order IDs, and status directly in their user profile (`/accounts/profile/`).

### 4. Admin Dashboard with Real-Time Business Insights
- **Authorized Admin Access:** Restricted to staff/superusers using Django's authentication and permission checks.
- **Core Real-Time Metrics:**
  - **Total Revenue:** Daily (Today), Weekly (Trailing 7 days), Monthly (MTD), and Yearly (YTD).
  - **Booking Trends:** Interactive Chart.js timeline of daily revenues and ticket volumes.
  - **Theater & Screen Occupancy Percentage:** Computed as `(Total Booked Seats ÷ Total Capacity of Shows in Range) × 100`.
  - **Most Booked Movies:** Ranking movies by tickets sold and gross revenue.
  - **Top-Performing Theaters:** Theaters sorted by occupancy rate and gross revenue.
  - **Peak Booking Hours:** 24-hour histogram (0h to 23h) generated via database `ExtractHour('created_at')`.
  - **Cancellations & Refunds:** Cancellation rate percentage, lost revenue, and auto-release metrics.
  - **User Growth:** Registration volume over time.
- **Custom Date Range Filter:** Custom start and end date pickers with live filtering.
- **CSV Data Exports:**
  - `/analytics/export/revenue/` (Daily revenue breakdown)
  - `/analytics/export/occupancy/` (Theater and screen occupancy metrics)
  - `/analytics/export/bookings/` (Detailed transaction records with streaming chunk iterator)

### 5. Movie Discovery with Search, Filters & Recommendations
- **Search Engine:** Search by movie title, synopsis keywords, and cast member names.
- **Faceted Filters:** Filter by Genre, Language, City, Theater, Release Status (Now Showing / Coming Soon), Minimum Rating (3★, 4★, 4.5★), and Show Timing (Morning, Afternoon, Evening, Night).
- **Multi-criteria Sorting:** Popularity / Trending, Newest releases, Highest rated, and Lowest ticket price.
- **Dynamic Counter:** Real-time badge displaying `"X Matching Movies"` after each filter.
- **Pagination:** Clean 8-movie-per-page pagination with previous/next controls.
- **Personalized Recommendations ("Recommended for You"):**
  - Evaluates user's previous confirmed bookings to identify favorite genres.
  - Inspects recently viewed movies (`UserRecentlyViewed`).
  - Fallbacks to top-rated trending releases for guest visitors.

### 6. Automated Ticket Generation & Email Confirmation
- **Boarding Pass PDF Ticket:** Generated using ReportLab with:
  - Cinema branding header, unique Booking ID (`CIN-2026-XXXXXX`)
  - Movie title, poster banner, screen type (IMAX 3D, Dolby Atmos)
  - Theater, screen, show date and start time
  - Booked seat codes (e.g., A4, A5), seat category (VIP Recliner, Premium, Regular)
  - Payment reference and total amount paid
  - Scannable QR Code generated via `qrcode` encoding the verification URL
- **Asynchronous Celery Email Processing:**
  - Dispatches `send_booking_confirmation_email_task(booking_id)` in the background without blocking checkout.
  - Automated retries (`max_retries=3`) with exponential backoff on delivery glitches.
- **Ticket Gatekeeper Verification Endpoint:**
  - `/bookings/verify/<uuid:token>/`: Scannable by cinema staff to verify ticket validity and execute digital check-in, permanently preventing ticket reuse.
- **Self-Service Downloads:** Patrons can download their tickets as PDFs anytime from the booking confirmation page or their profile history.

---

## ⚡ Performance Optimization for 100,000+ Bookings

To handle high concurrency and datasets with 100,000+ bookings efficiently:

1. **Database Indexing Architecture:**
   - `(show_date, start_time)`: Composite B-Tree index on `ShowSchedule` for sub-millisecond showtime queries.
   - `(status, created_at)`: Composite index on `Booking` and `PaymentTransaction` enabling instant date-range aggregations.
   - `(show, status, expires_at)`: Index on `SeatReservation` for high-frequency 2-minute expiration cleanups.
   - `(average_rating, is_trending)`: Composite index on `Movie` for instant sorting.

2. **In-Database SQL Aggregations:**
   - Zero Python-side list iterations for revenue or occupancy calculations. Aggregations run directly in the database engine using `Sum()`, `Count()`, `Avg()`, `TruncDate()`, and `ExtractHour()`.

3. **Memory-Safe CSV Streaming:**
   - CSV export endpoints utilize `QuerySet.iterator(chunk_size=1000)` to stream records without loading entire result sets into memory.

4. **Strict Concurrency Locking:**
   - `SeatReservation.reserve_seats_atomically` uses `select_for_update()` inside atomic transaction blocks to prevent duplicate seat locks.

---

## 🚀 Running the Project Locally

```bash
# 1. Run migrations
python manage.py migrate

# 2. Seed realistic database with movies, theaters, shows, bookings, and users
python manage.py seed_cinema_data

# 3. Run the development server
python manage.py runserver 127.0.0.1:8000

# 4. Run automated test suite
python manage.py test

# 5. Run end-to-end verification script
python verify_e2e_flow.py
```
