import random
from datetime import datetime, date, time, timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.utils.crypto import get_random_string

from accounts.models import User
from theaters.models import City, Theater, Screen, Seat, ShowSchedule
from movies.models import Genre, Language, CastMember, Movie, MovieCast, Review, ReviewReport
from bookings.models import Booking, BookingSeat, SeatReservation
from payments.models import PaymentTransaction


class Command(BaseCommand):
    help = 'Seeds complete cinema database with movies, theaters, screens, shows, verified bookings, reviews, and analytics data'

    def handle(self, *args, **options):
        self.stdout.write("Starting Cineverse Database Seeder...")

        # 1. Superuser / Admin
        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@cineverse.com',
                'first_name': 'Admin',
                'last_name': 'Director',
                'is_staff': True,
                'is_superuser': True,
            }
        )
        if created:
            admin_user.set_password('Admin@12345')
            admin_user.save()
            self.stdout.write(self.style.SUCCESS("Created admin user: admin / Admin@12345"))
        else:
            admin_user.set_password('Admin@12345')
            admin_user.is_staff = True
            admin_user.is_superuser = True
            admin_user.save()

        # 2. Verified Test Customer User
        test_user, created = User.objects.get_or_create(
            username='cinephile',
            defaults={
                'email': 'viewer@cineverse.com',
                'first_name': 'Aarav',
                'last_name': 'Sharma',
                'phone_number': '+919876543210',
                'loyalty_points': 350,
            }
        )
        if created:
            test_user.set_password('User@12345')
            test_user.save()
            self.stdout.write(self.style.SUCCESS("Created test user: cinephile / User@12345"))
        else:
            test_user.set_password('User@12345')
            test_user.save()

        # Community Users for reviews
        user_priya, _ = User.objects.get_or_create(
            username='priya_k',
            defaults={'email': 'priya@gmail.com', 'first_name': 'Priya', 'last_name': 'Kapoor'}
        )
        user_priya.set_password('User@12345')
        user_priya.save()

        user_rohit, _ = User.objects.get_or_create(
            username='rohit_m',
            defaults={'email': 'rohit@gmail.com', 'first_name': 'Rohit', 'last_name': 'Mehta'}
        )
        user_rohit.set_password('User@12345')
        user_rohit.save()

        # 3. Cities
        cities_data = [
            {'name': 'Mumbai', 'state': 'Maharashtra'},
            {'name': 'Delhi NCR', 'state': 'Delhi'},
            {'name': 'Bengaluru', 'state': 'Karnataka'},
            {'name': 'Hyderabad', 'state': 'Telangana'},
            {'name': 'Chennai', 'state': 'Tamil Nadu'},
        ]
        cities = {}
        for c in cities_data:
            city, _ = City.objects.get_or_create(name=c['name'], defaults={'state': c['state']})
            cities[c['name']] = city

        admin_user.preferred_city = cities['Mumbai']
        admin_user.save(update_fields=['preferred_city'])
        test_user.preferred_city = cities['Mumbai']
        test_user.save(update_fields=['preferred_city'])

        # 4. Theaters & Screens
        theaters_data = [
            {
                'name': 'Cineverse IMAX Palladium',
                'city': cities['Mumbai'],
                'address': 'High Street Phoenix, Senapati Bapat Marg, Lower Parel',
                'landmark': 'Next to Palladium Mall Entrance',
                'pincode': '400013',
                'facilities': 'IMAX Laser 3D, Dolby Atmos, Gourmet Food Lounge, Valet Parking, Wheelchair Accessible',
                'screens': [
                    {'name': 'Screen 1 - IMAX with Laser', 'type': 'IMAX_3D', 'rows': 7, 'cols': 12},
                    {'name': 'Screen 2 - Dolby Atmos 4K', 'type': 'DOLBY_ATMOS', 'rows': 6, 'cols': 10},
                ]
            },
            {
                'name': 'Cineverse Gold Class Bandra',
                'city': cities['Mumbai'],
                'address': 'Linking Road, Bandra West',
                'landmark': 'Opposite National College',
                'pincode': '400050',
                'facilities': 'Luxury VIP Recliners, Butler on Call, Dolby Atmos, Premium Dine-in',
                'screens': [
                    {'name': 'Auditorium 1 - Gold Class VIP', 'type': 'GOLD_CLASS', 'rows': 5, 'cols': 8},
                ]
            },
            {
                'name': 'Cineverse Select Citywalk Saket',
                'city': cities['Delhi NCR'],
                'address': 'Select Citywalk Mall, A-3 District Centre, Saket',
                'landmark': '3rd Floor Food Court Level',
                'pincode': '110017',
                'facilities': 'IMAX Laser, 4DX Motion, Dolby Atmos, Reserved Parking',
                'screens': [
                    {'name': 'Screen 1 - IMAX Experience', 'type': 'IMAX_3D', 'rows': 7, 'cols': 12},
                    {'name': 'Screen 2 - Dolby 7.1', 'type': 'STANDARD', 'rows': 6, 'cols': 10},
                ]
            },
            {
                'name': 'Cineverse Forum Koramangala',
                'city': cities['Bengaluru'],
                'address': 'Hosur Road, Koramangala 7th Block',
                'landmark': 'Forum Mall Top Floor',
                'pincode': '560095',
                'facilities': 'Dolby Atmos, 4DX Motion Seats, Gourmet Snacks, EV Charging',
                'screens': [
                    {'name': 'Screen 1 - Dolby Atmos Audi', 'type': 'DOLBY_ATMOS', 'rows': 6, 'cols': 10},
                    {'name': 'Screen 2 - 4DX Sensory', 'type': '4DX', 'rows': 5, 'cols': 8},
                ]
            },
            {
                'name': 'Cineverse Inorbit Mall Hitec City',
                'city': cities['Hyderabad'],
                'address': 'Inorbit Mall Road, Mindspace, Madhapur',
                'landmark': '4th Floor Multiplex Wing',
                'pincode': '500081',
                'facilities': 'IMAX Laser 3D, Dolby Atmos, VIP Lounge, Gaming Zone',
                'screens': [
                    {'name': 'Screen 1 - IMAX Big Screen', 'type': 'IMAX_3D', 'rows': 7, 'cols': 12},
                ]
            },
        ]

        all_screens = []
        for td in theaters_data:
            theater, _ = Theater.objects.get_or_create(
                city=td['city'],
                name=td['name'],
                defaults={
                    'address': td['address'],
                    'landmark': td['landmark'],
                    'pincode': td['pincode'],
                    'facilities': td['facilities'],
                }
            )

            for sd in td['screens']:
                screen, _ = Screen.objects.get_or_create(
                    theater=theater,
                    name=sd['name'],
                    defaults={
                        'screen_type': sd['type'],
                        'rows_count': sd['rows'],
                        'cols_count': sd['cols'],
                    }
                )
                all_screens.append(screen)

                # Generate Seats if screen has none
                if not screen.seats.exists():
                    seats_to_create = []
                    row_letters = [chr(65 + i) for i in range(sd['rows'])] # 'A', 'B', 'C'...

                    for r_idx, row_char in enumerate(row_letters):
                        # Determine seat type
                        if r_idx < 2:
                            s_type = 'REGULAR'
                            mult = Decimal('1.00')
                        elif r_idx < sd['rows'] - 1:
                            s_type = 'PREMIUM'
                            mult = Decimal('1.30')
                        else:
                            s_type = 'VIP_RECLINER'
                            mult = Decimal('1.70')

                        for col_num in range(1, sd['cols'] + 1):
                            code = f"{row_char}{col_num}"
                            seats_to_create.append(
                                Seat(
                                    screen=screen,
                                    row_identifier=row_char,
                                    seat_number=col_num,
                                    seat_code=code,
                                    seat_type=s_type,
                                    price_multiplier=mult,
                                )
                            )
                    Seat.objects.bulk_create(seats_to_create)
                    screen.recalculate_total_seats()

        # 5. Genres & Languages
        genre_names = ['Action', 'Sci-Fi', 'Drama', 'Thriller', 'Adventure', 'Comedy', 'Animation']
        genres = {}
        for g_name in genre_names:
            genre, _ = Genre.objects.get_or_create(name=g_name)
            genres[g_name] = genre

        langs_data = [
            {'name': 'English', 'code': 'EN'},
            {'name': 'Hindi', 'code': 'HI'},
            {'name': 'Telugu', 'code': 'TE'},
            {'name': 'Tamil', 'code': 'TA'},
        ]
        languages = {}
        for l in langs_data:
            lang, _ = Language.objects.get_or_create(name=l['name'], defaults={'code': l['code']})
            languages[l['code']] = lang

        # 6. Cast Members
        cast_data = [
            {'name': 'Christopher Nolan', 'role': 'DIRECTOR', 'bio': 'Visionary filmmaker known for complex narratives.'},
            {'name': 'Cillian Murphy', 'role': 'ACTOR', 'bio': 'Acclaimed Irish actor, Oscar winner for Oppenheimer.'},
            {'name': 'Leonardo DiCaprio', 'role': 'ACTOR', 'bio': 'Academy Award-winning American actor and producer.'},
            {'name': 'Denis Villeneuve', 'role': 'DIRECTOR', 'bio': 'French-Canadian director of Dune, Arrival, and Blade Runner 2049.'},
            {'name': 'Timothée Chalamet', 'role': 'ACTOR', 'bio': 'Star of Dune and Wonka.'},
            {'name': 'Zendaya', 'role': 'ACTOR', 'bio': 'Emmy Award-winning actress.'},
            {'name': 'Shah Rukh Khan', 'role': 'ACTOR', 'bio': 'The King of Indian Cinema.'},
            {'name': 'Deepika Padukone', 'role': 'ACTOR', 'bio': 'Leading Indian international superstar.'},
            {'name': 'Prabhas', 'role': 'ACTOR', 'bio': 'Indian megastar known for Baahubali and Kalki 2898 AD.'},
            {'name': 'Paul Mescal', 'role': 'ACTOR', 'bio': 'Leading Irish actor starring in Gladiator II.'},
        ]
        cast_members = {}
        for cd in cast_data:
            cm, _ = CastMember.objects.get_or_create(name=cd['name'], defaults={'role': cd['role'], 'bio': cd['bio']})
            cast_members[cd['name']] = cm

        # 7. Movies
        movies_data = [
            {
                'title': 'Dune: Part Two',
                'description': 'Paul Atreides unites with Chani and the Fremen while seeking revenge against the conspirators who destroyed his family. Facing a choice between the love of his life and the fate of the known universe, he endeavors to prevent a terrible future only he can foresee.',
                'duration': 166,
                'release_date': date(2024, 3, 1),
                'age_cert': 'UA 13+',
                'genres': ['Sci-Fi', 'Adventure', 'Action'],
                'languages': ['EN', 'HI'],
                'trailer': 'https://www.youtube.com/watch?v=Way9Dexny3w',
                'status': 'NOW_SHOWING',
                'is_trending': True,
                'cast': [('Denis Villeneuve', 'Director'), ('Timothée Chalamet', 'Paul Atreides'), ('Zendaya', 'Chani')]
            },
            {
                'title': 'Oppenheimer',
                'description': 'The story of American scientist J. Robert Oppenheimer and his role in the development of the atomic bomb during World War II, exploring the profound moral dilemmas and political backlash.',
                'duration': 180,
                'release_date': date(2023, 7, 21),
                'age_cert': 'A',
                'genres': ['Drama', 'Thriller'],
                'languages': ['EN', 'HI'],
                'trailer': 'https://www.youtube.com/watch?v=uYPbbksJxIg',
                'status': 'NOW_SHOWING',
                'is_trending': True,
                'cast': [('Christopher Nolan', 'Director'), ('Cillian Murphy', 'J. Robert Oppenheimer')]
            },
            {
                'title': 'Inception',
                'description': 'A thief who steals corporate secrets through the use of dream-sharing technology is given the inverse task of planting an idea into the mind of a C.E.O., but his tragic past may doom the project and his team to disaster.',
                'duration': 148,
                'release_date': date(2023, 8, 10),
                'age_cert': 'UA 13+',
                'genres': ['Action', 'Sci-Fi', 'Thriller'],
                'languages': ['EN', 'HI'],
                'trailer': 'https://www.youtube.com/watch?v=YoHD9XEInc0',
                'status': 'NOW_SHOWING',
                'is_trending': False,
                'cast': [('Christopher Nolan', 'Director'), ('Leonardo DiCaprio', 'Dom Cobb')]
            },
            {
                'title': 'Gladiator II',
                'description': 'Years after witnessing the death of the revered hero Maximus at the hands of his uncle, Lucius must enter the Colosseum after his home is conquered by the tyrannical Emperors who now lead Rome with an iron fist.',
                'duration': 148,
                'release_date': date(2024, 11, 15),
                'age_cert': 'A',
                'genres': ['Action', 'Drama', 'Adventure'],
                'languages': ['EN', 'HI'],
                'trailer': 'https://www.youtube.com/watch?v=4rgYUipGJNo',
                'status': 'NOW_SHOWING',
                'is_trending': True,
                'cast': [('Paul Mescal', 'Lucius')]
            },
            {
                'title': 'Kalki 2898 AD',
                'description': 'A modern avatar of the Hindu god Vishnu, believed to have descended to earth to protect the world from evil forces in a dystopian post-apocalyptic future set in the city of Kasi.',
                'duration': 181,
                'release_date': date(2024, 6, 27),
                'age_cert': 'UA 13+',
                'genres': ['Sci-Fi', 'Action'],
                'languages': ['TE', 'HI', 'TA'],
                'trailer': 'https://www.youtube.com/watch?v=kQDd1AhGIHk',
                'status': 'NOW_SHOWING',
                'is_trending': True,
                'cast': [('Prabhas', 'Bhairava'), ('Deepika Padukone', 'SUM-80')]
            },
            {
                'title': 'Avatar: Fire and Ash',
                'description': 'Jake Sully and Neytiri encounter the Ash People, a fiery and violent clan of Na\'vi, challenging their perception of Pandora and pushing their family to the absolute limit.',
                'duration': 192,
                'release_date': date(2025, 12, 19),
                'age_cert': 'UA 13+',
                'genres': ['Sci-Fi', 'Adventure', 'Action'],
                'languages': ['EN', 'HI', 'TE'],
                'trailer': 'https://www.youtube.com/watch?v=d9MyW72ELq0',
                'status': 'COMING_SOON',
                'is_trending': True,
                'cast': []
            },
        ]

        movies = {}
        for md in movies_data:
            movie, _ = Movie.objects.get_or_create(
                title=md['title'],
                defaults={
                    'description': md['description'],
                    'duration_minutes': md['duration'],
                    'release_date': md['release_date'],
                    'age_certification': md['age_cert'],
                    'youtube_trailer_url': md['trailer'],
                    'status': md['status'],
                    'is_trending': md['is_trending'],
                }
            )
            # Add genres and languages
            for g in md['genres']:
                movie.genres.add(genres[g])
            for l in md['languages']:
                movie.languages.add(languages[l])

            # Add cast entries
            for idx, (actor_name, character) in enumerate(md.get('cast', [])):
                if actor_name in cast_members:
                    MovieCast.objects.get_or_create(
                        movie=movie,
                        cast_member=cast_members[actor_name],
                        defaults={'character_name': character, 'order': idx}
                    )
            movies[md['title']] = movie

        # 8. Show Schedules (Past, Today, and Upcoming)
        today = timezone.now().date()
        times_slots = [
            time(10, 0),  # Morning
            time(13, 30), # Afternoon
            time(17, 45), # Evening
            time(21, 15), # Night
        ]

        shows_created = []

        # Create upcoming shows (next 5 days)
        for day_offset in range(5):
            s_date = today + timedelta(days=day_offset)
            for screen in all_screens:
                for movie_title in ['Dune: Part Two', 'Oppenheimer', 'Gladiator II', 'Kalki 2898 AD']:
                    m = movies[movie_title]
                    for t_slot in times_slots[:3]: # 3 shows per screen per day
                        base_p = Decimal('250.00') if screen.screen_type == 'STANDARD' else Decimal('350.00')
                        if screen.screen_type == 'GOLD_CLASS':
                            base_p = Decimal('550.00')

                        show, _ = ShowSchedule.objects.get_or_create(
                            movie=m,
                            screen=screen,
                            show_date=s_date,
                            start_time=t_slot,
                            defaults={
                                'base_price': base_p,
                                'status': 'SCHEDULED',
                            }
                        )
                        shows_created.append(show)

        # Create PAST shows (for watched movie verification and analytics history!)
        past_shows = []
        for past_day in [1, 2, 3, 5, 8, 12, 18, 25]:
            p_date = today - timedelta(days=past_day)
            for screen in all_screens[:3]:
                for movie_title in ['Oppenheimer', 'Dune: Part Two', 'Inception']:
                    m = movies[movie_title]
                    show, _ = ShowSchedule.objects.get_or_create(
                        movie=m,
                        screen=screen,
                        show_date=p_date,
                        start_time=time(18, 0),
                        defaults={
                            'base_price': Decimal('320.00'),
                            'status': 'COMPLETED',
                        }
                    )
                    past_shows.append(show)

        self.stdout.write(f"Created {len(shows_created)} upcoming shows and {len(past_shows)} past shows.")

        # 9. Confirmed Bookings for test_user ('cinephile') to verify VERIFIED VIEWER BADGE
        watched_show_1 = past_shows[0]  # Oppenheimer in the past
        watched_show_2 = past_shows[1]  # Dune: Part Two in the past

        for idx, show in enumerate([watched_show_1, watched_show_2]):
            booking_id = f"CIN-2026-PAST0{idx+1}"
            b, created = Booking.objects.get_or_create(
                booking_id=booking_id,
                defaults={
                    'user': test_user,
                    'show': show,
                    'total_ticket_amount': Decimal('640.00'),
                    'convenience_fee': Decimal('30.00'),
                    'final_amount': Decimal('670.00'),
                    'status': 'CONFIRMED',
                    'is_checked_in': True,
                    'checked_in_at': timezone.now() - timedelta(days=2),
                }
            )
            if created:
                b.created_at = timezone.now() - timedelta(days=3)
                b.save()

                seats = list(show.screen.seats.all()[:2])
                for s in seats:
                    BookingSeat.objects.create(
                        booking=b,
                        seat=s,
                        seat_code=s.seat_code,
                        seat_type=s.get_seat_type_display(),
                        price=show.calculate_seat_price(s)
                    )
                    SeatReservation.objects.create(
                        show=show,
                        seat=s,
                        user=test_user,
                        session_key='seeded_session',
                        status='BOOKED',
                        expires_at=timezone.now() + timedelta(days=365),
                        booking=b
                    )

                PaymentTransaction.objects.create(
                    booking=b,
                    user=test_user,
                    gateway='RAZORPAY',
                    transaction_id=f"pay_seeded_{b.booking_id}",
                    order_id=f"order_{b.booking_id}",
                    amount=b.final_amount,
                    status='SUCCESS',
                    raw_response={'seeded': True},
                )

        # 10. Generate historical bookings over the past 30 days for rich Analytics Insights
        self.stdout.write("Generating historical booking data for business insights...")
        all_past_and_current_shows = past_shows + shows_created[:10]
        customers = [test_user, user_priya, user_rohit, admin_user]

        for i in range(40):
            show = random.choice(all_past_and_current_shows)
            user = random.choice(customers)
            b_status = 'CONFIRMED' if i % 6 != 0 else 'CANCELLED' # 16% cancellations
            created_days_ago = random.randint(0, 28)
            booking_dt = timezone.now() - timedelta(days=created_days_ago, hours=random.randint(1, 23))

            b_id = f"CIN-2026-STAT{i:03d}"
            b, b_created = Booking.objects.get_or_create(
                booking_id=b_id,
                defaults={
                    'user': user,
                    'show': show,
                    'total_ticket_amount': Decimal('700.00'),
                    'convenience_fee': Decimal('30.00'),
                    'final_amount': Decimal('730.00'),
                    'status': b_status,
                }
            )
            if b_created:
                # Override created_at for analytics aggregation
                Booking.objects.filter(id=b.id).update(created_at=booking_dt)
                
                # Pick available seats for this booking
                screen_seats = list(show.screen.seats.all()[:3])
                for s in screen_seats:
                    BookingSeat.objects.create(
                        booking=b,
                        seat=s,
                        seat_code=s.seat_code,
                        seat_type=s.get_seat_type_display(),
                        price=show.calculate_seat_price(s)
                    )

                # Payment Transaction
                p_status = 'SUCCESS' if b_status == 'CONFIRMED' else 'REFUNDED'
                txn = PaymentTransaction.objects.create(
                    booking=b,
                    user=user,
                    gateway='RAZORPAY',
                    transaction_id=f"txn_hist_{b_id}",
                    order_id=f"order_hist_{b_id}",
                    amount=b.final_amount,
                    status=p_status,
                    raw_response={'analytics_test': True}
                )
                PaymentTransaction.objects.filter(id=txn.id).update(created_at=booking_dt)

        # 11. Seed Verified Viewer Reviews for Oppenheimer & Dune
        oppenheimer = movies['Oppenheimer']
        dune = movies['Dune: Part Two']

        # Review 1 by test_user ('cinephile') - verified!
        rev1, _ = Review.objects.get_or_create(
            movie=oppenheimer,
            user=test_user,
            defaults={
                'rating': 5,
                'title': 'A Masterclass in Tension, Editing, and Sound Design',
                'content': 'Watching this on the 70mm IMAX format in Cineverse was an unforgettable auditory and visual experience. Cillian Murphy delivers the performance of his career. The Trinity test scene was pure cinematic silence and devastation.',
                'is_verified_viewer': True,
                'is_approved': True,
            }
        )

        # Review 2 by Priya
        rev2, _ = Review.objects.get_or_create(
            movie=oppenheimer,
            user=user_priya,
            defaults={
                'rating': 5,
                'title': 'Spectacular biopic that feels like a political thriller',
                'content': 'Ludwig Göransson’s score keeps your heart racing for 3 full hours. Absolutely loved the pacing and cinematography.',
                'is_verified_viewer': True,
                'is_approved': True,
            }
        )

        # Review 3 for Dune: Part Two
        rev3, _ = Review.objects.get_or_create(
            movie=dune,
            user=test_user,
            defaults={
                'rating': 5,
                'title': 'Science fiction on a scale we haven\'t seen since The Lord of the Rings',
                'content': 'Denis Villeneuve has crafted a timeless masterpiece. The sandworm riding sequence and the gladiatorial battle on Giedi Prime were astonishing in IMAX 3D.',
                'is_verified_viewer': True,
                'is_approved': True,
            }
        )

        # Review 4: Reported Review (to demonstrate inappropriate content moderation!)
        spam_user, _ = User.objects.get_or_create(username='bot_tester', defaults={'email': 'bot@spam.com'})
        rev_spam, _ = Review.objects.get_or_create(
            movie=dune,
            user=spam_user,
            defaults={
                'rating': 1,
                'title': 'Free download movie links click here www.spam-fake.com',
                'content': 'Visit my free site for full HD downloads and casino bonuses! Do not buy tickets.',
                'is_verified_viewer': False,
                'is_flagged': True,
                'is_approved': False,
            }
        )
        ReviewReport.objects.get_or_create(
            review=rev_spam,
            reporter=test_user,
            defaults={
                'reason': 'SPAM',
                'details': 'Promotional link spam violating community guidelines.',
                'status': 'PENDING'
            }
        )

        # Recalculate movie rating stats
        oppenheimer.recalculate_rating_stats()
        dune.recalculate_rating_stats()

        self.stdout.write(self.style.SUCCESS("Database seeding completed successfully!"))
        self.stdout.write(self.style.SUCCESS("All movies, showtimes, verified bookings, reviews, and analytics are ready."))
