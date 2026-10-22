"""
DeKUT campus venues — single source of truth.

Used by:
  * seed.py            -> realistic locations for seeded events
  * GET /venues        -> populates the Location picker on Create/Edit Event
  * (optionally) the report, to show where venue data came from

Every entry records where the information came from:
  "official"  = dkut.ac.ke (University Profile 2021 PDF, Library pages)
  "secondary" = third-party description of the campus (e.g. Wikipedia)
  "unverified"= plausible room name that still needs a physical check

Capacities are ONLY filled in where a source states them. Never guess.
"""

from typing import TypedDict


class Venue(TypedDict):
    name: str
    area: str            # Main Campus (Nyeri) | Nairobi Campus | Conservancy | Online
    kind: str            # hall | lab | hub | library | sports | outdoor | online
    categories: list[str]  # event categories this venue suits
    capacity: int | None
    source: str          # official | secondary | unverified
    note: str


MAIN = "Main Campus (Nyeri)"
NAIROBI = "Nairobi Campus"
CONSERVANCY = "DeKUT Wildlife Conservancy"
ONLINE = "Online"

VENUES: list[Venue] = [
    # ── Learning spaces ───────────────────────────────────────────────
    {"name": "Resource Centre 1 Library", "area": MAIN, "kind": "library",
     "categories": ["Academic", "Workshop"], "capacity": None, "source": "official",
     "note": "Main library, 2nd floor of Resource Centre 1. Open Mon-Fri 8am-9pm, Sat 9am-4pm, closed Sundays and public holidays."},
    {"name": "Resource Centre 3 Library", "area": MAIN, "kind": "library",
     "categories": ["Academic", "Workshop"], "capacity": None, "source": "official",
     "note": "Library space on the 3rd floor of Resource Centre 3. Same opening hours as the main library."},
    {"name": "Resource Centre (RC) Lecture Theatres", "area": MAIN, "kind": "hall",
     "categories": ["Academic", "Workshop", "Career"], "capacity": None, "source": "official",
     "note": "dkut.ac.ke: the Resource Centre (phases 1-2) comprises lecture theatres, library, laboratories and offices. Individual theatre names/capacities are not published; confirm on site."},
    {"name": "Resource Centre (RC) Computer Laboratories", "area": MAIN, "kind": "lab",
     "categories": ["Academic", "Workshop", "Tech"], "capacity": None, "source": "secondary",
     "note": "Computer labs inside the Resource Centre. Individual lab names not published; confirm on site."},
    {"name": "Academic Block Lecture Rooms", "area": MAIN, "kind": "hall",
     "categories": ["Academic", "Workshop"], "capacity": None, "source": "secondary",
     "note": "The Academic Block houses lecture rooms, ICT labs, engineering labs, workshops and physics/chemistry labs (Wikipedia)."},
    {"name": "Academic Block ICT Labs", "area": MAIN, "kind": "lab",
     "categories": ["Tech", "Workshop", "Academic"], "capacity": None, "source": "secondary",
     "note": "ICT labs in the Academic Block (Wikipedia)."},
    {"name": "Academic Block Engineering Labs & Workshops", "area": MAIN, "kind": "lab",
     "categories": ["Workshop", "Academic", "Tech"], "capacity": None, "source": "secondary",
     "note": "Engineering labs and workshops in the Academic Block (Wikipedia)."},
    {"name": "DeKUT Freedom Hall", "area": MAIN, "kind": "hall",
     "categories": ["Social", "Cultural", "Academic"], "capacity": None, "source": "official",
     "note": "Main campus hall. Hosted the Academic Open Day, the Chaplaincy Policy launch and student leaders' induction. Capacity not published."},

    # ── Innovation & enterprise ───────────────────────────────────────
    {"name": "DeHUB (Innovation & Incubation Hub)", "area": MAIN, "kind": "hub",
     "categories": ["Tech", "Workshop", "Career"], "capacity": None, "source": "official",
     "note": "Hosts incubation, mentoring meetups, and 'Hack Rush' mini-hackathons every fortnight (Fri 7pm to Sat 7pm)."},
    {"name": "DeKUT Film, Animation & Gaming Hub", "area": MAIN, "kind": "hub",
     "categories": ["Cultural", "Tech", "Workshop"], "capacity": None, "source": "official",
     "note": "Part of the Science & Technology Park. Scripting, filming, voice recording, 2D/3D animation, video gaming. Open to students, staff and the public."},
    {"name": "Dedan Kimathi Science & Technology Park (DeST-Park)", "area": MAIN, "kind": "hub",
     "categories": ["Tech", "Career", "Workshop"], "capacity": None, "source": "official",
     "note": "stp.dkut.ac.ke: ~6 km from Nyeri town. Focus on bio-resources/agri-tech, ICT, and Design-Materials-Manufacturing. Hosts capacity-building workshops, leases built space to startups."},
    {"name": "DeKUT Startup Centre (DeStaC)", "area": MAIN, "kind": "hub",
     "categories": ["Career", "Tech"], "capacity": None, "source": "official",
     "note": "Runs startup fairs and the startup support cycle."},
    {"name": "Centre for Innovation & Entrepreneurship Management (CIEM)", "area": MAIN, "kind": "hub",
     "categories": ["Career", "Workshop"], "capacity": None, "source": "official",
     "note": "Entrepreneurship training, e.g. the E4E programme and Startup Fair."},
    {"name": "Siemens Centre", "area": MAIN, "kind": "lab",
     "categories": ["Workshop", "Tech", "Academic"], "capacity": None, "source": "official",
     "note": "Mechatronics certification and skills competitions."},
    {"name": "Centre for Data Science & AI", "area": MAIN, "kind": "lab",
     "categories": ["Tech", "Academic"], "capacity": None, "source": "official",
     "note": "Listed among the university's research centres."},
    {"name": "Software Development Centre", "area": MAIN, "kind": "lab",
     "categories": ["Tech", "Workshop"], "capacity": None, "source": "official",
     "note": "Listed among the university's research centres."},
    {"name": "Coffee Technology & Food Safety Centre", "area": MAIN, "kind": "lab",
     "categories": ["Academic", "Workshop", "Cultural"], "capacity": None, "source": "official",
     "note": "Coffee cupping facilities and coffee-value-chain tours."},

    # ── Social & sports ───────────────────────────────────────────────
    {"name": "Students' Centre", "area": MAIN, "kind": "hall",
     "categories": ["Social", "Cultural"], "capacity": None, "source": "secondary",
     "note": "Social space with TV and pool tables."},
    {"name": "Rugby Field", "area": MAIN, "kind": "sports",
     "categories": ["Sports", "Social"], "capacity": None, "source": "secondary",
     "note": "Main rugby/football field."},
    {"name": "Basketball, Volleyball & Badminton Courts", "area": MAIN, "kind": "sports",
     "categories": ["Sports"], "capacity": None, "source": "secondary",
     "note": "Outdoor courts."},
    {"name": "Hockey Pitch", "area": MAIN, "kind": "sports",
     "categories": ["Sports"], "capacity": None, "source": "secondary",
     "note": "Field hockey pitch."},
    {"name": "DeKUT Challenge Course", "area": MAIN, "kind": "outdoor",
     "categories": ["Social", "Sports"], "capacity": None, "source": "official",
     "note": "Team-building course."},

    # ── Conservancy (off the main academic area, 7 km from Nyeri town) ──
    {"name": "Conservancy Conference Hall", "area": CONSERVANCY, "kind": "hall",
     "categories": ["Academic", "Career", "Social"], "capacity": 80, "source": "official",
     "note": "80 seated. For meetings, retreats, seminars and workshops."},
    {"name": "Conservancy Campsite", "area": CONSERVANCY, "kind": "outdoor",
     "categories": ["Social", "Cultural"], "capacity": 50, "source": "official",
     "note": "Capacity 50, lit, space for a bonfire and barbecue."},
    {"name": "Conservancy Open Grounds", "area": CONSERVANCY, "kind": "outdoor",
     "categories": ["Social", "Sports"], "capacity": None, "source": "official",
     "note": "Grass grounds for team-building games, picnics and gatherings."},

    # ── Other campuses / online ───────────────────────────────────────
    {"name": "Nairobi Campus (Pension Towers, Loita St)", "area": NAIROBI, "kind": "hall",
     "categories": ["Academic", "Career", "Workshop"], "capacity": None, "source": "official",
     "note": "Nairobi CBD campus on the 2nd, 9th and 13th floors of Pension Towers, Loita Street; library on the 9th floor."},
    {"name": "Online (Zoom / Google Meet)", "area": ONLINE, "kind": "online",
     "categories": ["Academic", "Social", "Sports", "Workshop", "Cultural", "Tech", "Career"],
     "capacity": None, "source": "official", "note": "Virtual events."},
]

ONLINE_NAME = "Online (Zoom / Google Meet)"

# Sports events must not land in a library, and so on.
_BY_CATEGORY: dict[str, list[Venue]] = {}
for _v in VENUES:
    for _c in _v["categories"]:
        _BY_CATEGORY.setdefault(_c, []).append(_v)


def venues_for(category: str, *, include_online: bool = False) -> list[Venue]:
    """Venues that suit an event category (physical venues only by default)."""
    found = _BY_CATEGORY.get(category, VENUES)
    return found if include_online else [v for v in found if v["kind"] != "online"]
