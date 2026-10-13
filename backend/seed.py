"""
Seed script for the DeKUT Event Management System.

Creates ~80 synthetic future events, ~20 users with deliberate interest
profiles, and RSVPs that are consistent with those interests.

Run from the backend directory:
    python seed.py

The GROUND_TRUTH dict at the bottom records which events each user
*should* be recommended — used by ml/evaluate.py to compute precision.
"""

import json
import random
import uuid
from datetime import datetime, timedelta, timezone

from app.database import Base, engine, SessionLocal
from app.models.user import User
from app.models.event import Event
from app.models.rsvp import RSVP
from app.models.user_interest import UserInterest
from app.services.auth import hash_password

# ── Constants ─────────────────────────────────────────────────────────

CATEGORIES = ["Academic", "Social", "Sports", "Workshop", "Cultural", "Tech", "Career"]

# Shared tag vocabulary — each event will sample 2-4 of these based on
# its category. Users will declare interest in subsets of these tags.
TAG_POOL = {
    "Academic":   ["research", "lecture", "seminar", "thesis", "study group", "journal club", "science", "mathematics"],
    "Social":     ["networking", "party", "mixer", "community", "games", "bonfire", "picnic", "karaoke"],
    "Sports":     ["football", "basketball", "athletics", "volleyball", "rugby", "fitness", "marathon", "swimming"],
    "Workshop":   ["hands-on", "training", "certification", "bootcamp", "beginner", "advanced", "skills"],
    "Cultural":   ["music", "dance", "art", "film", "theatre", "poetry", "fashion", "heritage"],
    "Tech":       ["python", "javascript", "ai", "data science", "cybersecurity", "web development", "mobile", "cloud", "iot", "blockchain"],
    "Career":     ["internship", "resume", "interview", "entrepreneurship", "startup", "leadership", "mentorship", "freelancing"],
}

LOCATIONS = [
    "Main Hall", "Lecture Theatre 1", "Lecture Theatre 2", "Science Lab",
    "Library Auditorium", "Sports Complex", "Innovation Hub", "Student Centre",
    "Cafeteria Courtyard", "Open Grounds", "Computer Lab 3", "Engineering Block",
    "Arts Studio", "Business Incubator", "Virtual (Zoom)",
]

# ── Event Templates ───────────────────────────────────────────────────
# Each template: (title, description, category, extra_tags)

EVENT_TEMPLATES = [
    # Academic (12)
    ("Research Methods Seminar",           "An in-depth seminar covering qualitative and quantitative research methods for final-year students.",  "Academic",  ["research", "seminar"]),
    ("Physics Study Group",                "Weekly study sessions for PHY 301. Bring your problem sets!",                                          "Academic",  ["study group", "science"]),
    ("Mathematics Olympiad Prep",          "Preparation workshop for the upcoming inter-university Maths Olympiad.",                               "Academic",  ["mathematics", "seminar"]),
    ("Thesis Writing Workshop",            "Learn how to structure your thesis, cite sources, and manage your timeline.",                           "Academic",  ["thesis", "seminar"]),
    ("Journal Club: AI in Medicine",       "Discuss the latest papers on AI applications in healthcare.",                                          "Academic",  ["journal club", "ai", "science"]),
    ("Data Structures Masterclass",        "Deep dive into trees, graphs, and dynamic programming.",                                               "Academic",  ["lecture", "science"]),
    ("Chemistry Lab Open Day",             "Tour the new analytical chemistry lab and see live demonstrations.",                                   "Academic",  ["science", "lecture"]),
    ("Academic Writing Clinic",            "One-on-one feedback on your academic papers and essays.",                                              "Academic",  ["thesis", "research"]),
    ("Environmental Science Talk",         "Guest lecture on climate change impacts in East Africa.",                                              "Academic",  ["lecture", "science", "research"]),
    ("Statistics Bootcamp",                "Crash course in statistics for data-driven research projects.",                                        "Academic",  ["seminar", "science", "data science"]),
    ("Peer Review Session",                "Bring your draft paper for constructive peer feedback.",                                               "Academic",  ["research", "journal club"]),
    ("GIS and Remote Sensing Intro",       "Introduction to Geographic Information Systems for environmental studies.",                            "Academic",  ["science", "lecture"]),

    # Social (11)
    ("Freshers' Welcome Mixer",            "Meet your classmates and make new friends at this casual mixer.",                                      "Social",    ["mixer", "community"]),
    ("Campus Bonfire Night",               "S'mores, music, and stories under the stars.",                                                        "Social",    ["bonfire", "community"]),
    ("Board Games Afternoon",              "Bring your favourite board games or try something new.",                                               "Social",    ["games", "community"]),
    ("International Food Festival",        "Taste dishes from around the world prepared by fellow students.",                                      "Social",    ["community", "networking"]),
    ("Karaoke Night",                      "Show off your singing skills (or lack thereof!) at the student centre.",                               "Social",    ["karaoke", "party"]),
    ("Networking Brunch",                  "Casual brunch with alumni and industry professionals.",                                                "Social",    ["networking", "mixer"]),
    ("Movie Night: Sci-Fi Marathon",       "Three classic sci-fi films back to back in the auditorium.",                                           "Social",    ["community", "games"]),
    ("Campus Cleanup Drive",               "Volunteer to clean up the campus grounds and win prizes.",                                             "Social",    ["community", "networking"]),
    ("Speed Friending Event",              "Timed conversations to help you meet people outside your course.",                                     "Social",    ["mixer", "networking"]),
    ("Cultural Exchange Evening",          "Share stories and traditions from your home region.",                                                  "Social",    ["community", "networking"]),
    ("Outdoor Picnic & Frisbee",           "Relax on the open grounds with snacks and frisbee.",                                                  "Social",    ["picnic", "games"]),

    # Sports (11)
    ("Inter-Faculty Football Tournament",  "5-a-side football. Register your faculty team by Friday.",                                            "Sports",    ["football", "fitness"]),
    ("Basketball Skills Clinic",           "Improve your dribbling, shooting, and defense with Coach Mwangi.",                                    "Sports",    ["basketball", "fitness"]),
    ("Campus Marathon 2026",               "5K and 10K routes through the campus and surrounding trails.",                                        "Sports",    ["marathon", "athletics", "fitness"]),
    ("Volleyball Beach Day",               "Sand volleyball at the sports complex. Teams of 6.",                                                  "Sports",    ["volleyball", "fitness"]),
    ("Rugby Sevens Invitational",          "Watch DeKUT take on visiting universities in fast-paced rugby.",                                      "Sports",    ["rugby", "athletics"]),
    ("Swimming Gala",                      "Competitive and fun swimming events for all skill levels.",                                           "Sports",    ["swimming", "fitness"]),
    ("Fitness Bootcamp",                   "High-intensity interval training led by a certified trainer.",                                        "Sports",    ["fitness", "marathon"]),
    ("Table Tennis Open",                  "Singles and doubles tournament — all welcome.",                                                       "Sports",    ["athletics", "games"]),
    ("Yoga & Mindfulness Session",         "Relax your body and mind with guided yoga on the lawn.",                                              "Sports",    ["fitness", "swimming"]),
    ("Athletics Time Trials",              "Track your 100m, 200m, and 400m times before the nationals.",                                         "Sports",    ["athletics", "marathon"]),
    ("Badminton Doubles League",           "Weekly league matches — sign up with a partner.",                                                     "Sports",    ["athletics", "fitness"]),

    # Workshop (12)
    ("Python for Beginners",               "Hands-on workshop: install Python, write your first script, and build a mini project.",               "Workshop",  ["python", "beginner", "hands-on"]),
    ("Web Development Bootcamp",           "Build a responsive website from scratch using HTML, CSS, and JavaScript.",                            "Workshop",  ["web development", "javascript", "bootcamp"]),
    ("Data Science with Pandas",           "Learn data manipulation, visualization, and analysis with pandas and matplotlib.",                    "Workshop",  ["data science", "python", "hands-on"]),
    ("Cybersecurity Essentials",           "Understand common threats, encryption basics, and how to stay safe online.",                          "Workshop",  ["cybersecurity", "training"]),
    ("Mobile App Development",             "Build a cross-platform mobile app with React Native in one day.",                                    "Workshop",  ["mobile", "javascript", "bootcamp"]),
    ("Cloud Computing 101",                "Introduction to AWS, GCP, and Azure — deploy your first cloud app.",                                 "Workshop",  ["cloud", "training", "beginner"]),
    ("IoT with Raspberry Pi",              "Connect sensors, actuators, and the internet using Raspberry Pi.",                                   "Workshop",  ["iot", "hands-on", "python"]),
    ("Machine Learning Crash Course",      "Supervised learning, model evaluation, and scikit-learn basics.",                                    "Workshop",  ["ai", "data science", "python", "bootcamp"]),
    ("Blockchain & Smart Contracts",       "Write and deploy a simple smart contract on Ethereum.",                                              "Workshop",  ["blockchain", "hands-on"]),
    ("Advanced JavaScript Patterns",       "Closures, async/await, and design patterns for production JS.",                                     "Workshop",  ["javascript", "advanced"]),
    ("Linux Command Line Mastery",         "Navigate, script, and automate with the Linux terminal.",                                            "Workshop",  ["training", "skills", "beginner"]),
    ("UI/UX Design Fundamentals",          "Wireframing, prototyping, and user testing with Figma.",                                             "Workshop",  ["hands-on", "skills", "beginner"]),

    # Cultural (11)
    ("DeKUT Music Fest",                   "Live performances by student bands and solo artists.",                                               "Cultural",  ["music", "community"]),
    ("African Dance Workshop",             "Learn traditional East African dance styles with live drumming.",                                    "Cultural",  ["dance", "heritage"]),
    ("Poetry Slam Night",                  "Perform your original poetry or just enjoy the spoken word.",                                        "Cultural",  ["poetry", "art"]),
    ("Short Film Screening",              "Watch award-winning short films by Kenyan filmmakers.",                                              "Cultural",  ["film", "art"]),
    ("Fashion Show: AfroChic",             "Student-designed fashion inspired by African heritage.",                                             "Cultural",  ["fashion", "heritage"]),
    ("Theatre Production: The Trial",      "The drama club performs Arthur Miller's 'The Trial'.",                                               "Cultural",  ["theatre", "art"]),
    ("Art Exhibition: Perspectives",       "Mixed-media artwork by fine arts students on display for a week.",                                   "Cultural",  ["art", "heritage"]),
    ("Guitar Masterclass",                 "Learn chords, fingerpicking, and songwriting tips.",                                                 "Cultural",  ["music", "hands-on"]),
    ("Cultural Heritage Day",              "Celebrate Kenya's diverse cultures with food, dress, and song.",                                     "Cultural",  ["heritage", "community"]),
    ("Photography Walk",                   "Capture campus beauty with tips from a professional photographer.",                                  "Cultural",  ["art", "film"]),
    ("Open Mic Comedy Night",              "Stand-up, improv, and jokes — audience participation welcome.",                                      "Cultural",  ["community", "theatre"]),

    # Tech (12)
    ("DeKUT Hackathon 2026",               "48-hour hackathon — build a solution to a real community problem.",                                  "Tech",      ["python", "javascript", "ai", "web development"]),
    ("AI & Ethics Panel",                  "Panel discussion on responsible AI development and deployment.",                                     "Tech",      ["ai", "data science"]),
    ("Cybersecurity CTF Challenge",        "Capture The Flag competition — test your hacking skills ethically.",                                 "Tech",      ["cybersecurity", "python"]),
    ("Open Source Contribution Day",       "Pick a project, submit a PR, and learn collaborative development.",                                 "Tech",      ["python", "javascript", "web development"]),
    ("DevOps & CI/CD Pipeline Workshop",   "Set up automated testing and deployment with GitHub Actions.",                                      "Tech",      ["cloud", "web development"]),
    ("Data Visualization with D3.js",      "Create interactive charts and dashboards using D3.js.",                                              "Tech",      ["javascript", "data science", "web development"]),
    ("Intro to Blockchain",                "Understand distributed ledgers, consensus, and use cases.",                                          "Tech",      ["blockchain", "iot"]),
    ("IoT Smart Campus Project",           "Prototype smart sensors for energy monitoring on campus.",                                           "Tech",      ["iot", "python"]),
    ("Mobile UX Testing Workshop",         "Test your mobile app's usability with real users.",                                                  "Tech",      ["mobile", "web development"]),
    ("Cloud Architecture Deep Dive",       "Design scalable cloud infrastructure for microservices.",                                            "Tech",      ["cloud", "web development"]),
    ("Tech Talk: Future of Computing",     "Guest speaker from Google on quantum and neuromorphic computing.",                                   "Tech",      ["ai", "cloud"]),
    ("API Design Best Practices",          "RESTful patterns, versioning, and documentation with FastAPI.",                                      "Tech",      ["python", "web development"]),

    # Career (11)
    ("Resume Building Workshop",           "Craft a compelling resume that stands out to recruiters.",                                           "Career",    ["resume", "skills"]),
    ("Mock Interview Day",                 "Practice behavioural and technical interviews with real panellists.",                                "Career",    ["interview", "mentorship"]),
    ("Entrepreneurship Bootcamp",          "From idea to pitch: learn to build a startup business plan.",                                       "Career",    ["entrepreneurship", "startup", "leadership"]),
    ("Freelancing 101",                    "How to find clients, set rates, and manage freelance projects.",                                    "Career",    ["freelancing", "startup"]),
    ("Tech Internship Fair",               "Meet recruiters from top tech companies hiring interns.",                                            "Career",    ["internship", "interview"]),
    ("Leadership Summit",                  "Develop leadership skills through interactive workshops.",                                          "Career",    ["leadership", "mentorship"]),
    ("Personal Branding Workshop",         "Build your online presence on LinkedIn and GitHub.",                                                "Career",    ["resume", "networking"]),
    ("Women in Tech Mentorship",           "Mentorship circles for women pursuing careers in technology.",                                      "Career",    ["mentorship", "leadership"]),
    ("Startup Pitch Competition",          "Present your startup idea to a panel of investors and mentors.",                                    "Career",    ["startup", "entrepreneurship"]),
    ("Alumni Career Panel",                "Hear from DeKUT alumni about their career journeys.",                                               "Career",    ["mentorship", "interview"]),
    ("Financial Literacy for Students",    "Budgeting, saving, and investing basics for university students.",                                  "Career",    ["skills", "leadership"]),

    # Additional Academic (12)
    ("Engineering Dynamics Review",        "Comprehensive tutorial on dynamics and thermodynamics problems for engineering students.",           "Academic",  ["science", "lecture"]),
    ("Epidemiology Case Studies",          "Analyzing disease surveillance data in rural health centers.",                                      "Academic",  ["science", "research"]),
    ("Econometrics Applied Workshop",      "Empirical modeling and regression with economic panel datasets.",                                    "Academic",  ["research", "data science"]),
    ("Digital Signal Processing Seminar",  "Fourier transforms and filter design in telecommunications.",                                        "Academic",  ["science", "lecture"]),
    ("Bioinformatics Colloquium",          "Genomic sequence analysis using Python and BioPython libraries.",                                    "Academic",  ["science", "python", "ai"]),
    ("Embedded Systems Research Forum",    "Microcontrollers, RTOS, and sensor interfacing in smart agriculture.",                               "Academic",  ["science", "iot"]),
    ("Renewable Energy Symposium",         "Solar microgrids and wind integration in Central Kenya highlands.",                                  "Academic",  ["science", "research"]),
    ("Applied Linear Algebra Clinic",      "Eigenvalues, SVD decompositions, and PCA for engineering applications.",                             "Academic",  ["mathematics", "seminar"]),
    ("Clinical Nursing Skills Review",     "Best practices in patient triage, wound management, and emergency care.",                            "Academic",  ["science", "seminar"]),
    ("Business Law and Ethics Lecture",    "Intellectual property rights, patent filing, and startup governance in Kenya.",                      "Academic",  ["lecture", "seminar"]),
    ("Algorithms for Competitive Coding",  "Advanced graph traversal, segment trees, and dynamic programming.",                                  "Academic",  ["science", "python"]),
    ("Computer Vision Reading Group",      "Reviewing papers on vision transformers, object detection, and medical imaging.",                    "Academic",  ["ai", "research", "python"]),

    # Additional Social (11)
    ("Campus Trivia Bowl",                 "General knowledge, pop culture, and science trivia championship.",                                   "Social",    ["games", "community"]),
    ("Acoustic Sunset Jam",                "Unplugged acoustic music session by the cafeteria courtyard.",                                       "Social",    ["community", "karaoke"]),
    ("Hostel Blitz Chess Tournament",      "Casual speed chess games open to all resident and day scholars.",                                    "Social",    ["games", "community"]),
    ("Campus Stargazing Night",            "Telescope viewing, constellations, and astronomy lore on the sports field.",                         "Social",    ["community", "picnic"]),
    ("Outdoor Cinema: African Cinema",     "Screening acclaimed East African contemporary films under the stars.",                               "Social",    ["community", "party"]),
    ("Salsa & Social Dance Evening",       "Beginner partner dance lessons followed by an open social dance.",                                   "Social",    ["mixer", "community"]),
    ("DeKUT Gaming LAN Party",             "Competitive multiplayer tournaments in FIFA, Tekken, and Call of Duty.",                            "Social",    ["games", "community"]),
    ("Alumni Mentorship Mixer",            "Speed networking and conversational circles with recent graduates.",                                 "Social",    ["networking", "mixer"]),
    ("Charity Bake Sale & Fair",           "Fundraising fair for local primary school digital libraries.",                                       "Social",    ["community", "party"]),
    ("Campus Comedy Showcase",             "Stand-up comedy and improv performances by talented student comics.",                                "Social",    ["party", "community"]),
    ("Weekend Hiking Expedition",          "Scenic day hike to Mount Kenya foothills nature trails.",                                            "Social",    ["picnic", "community"]),

    # Additional Sports (11)
    ("Inter-Hostel Football Derby",        "Rival hostels clash in the annual campus cup quarter-finals.",                                       "Sports",    ["football", "athletics"]),
    ("3-on-3 Street Basketball Showdown",  "Half-court tournament with music, refereeing, and dunk exhibitions.",                                "Sports",    ["basketball", "fitness"]),
    ("DeKUT Cross Country Run",            "8KM off-road race across hilly forest trails surrounding Nyeri campus.",                             "Sports",    ["marathon", "athletics"]),
    ("Martial Arts & Self-Defense",        "Practical self-defense techniques, situational awareness, and sparring drills.",                     "Sports",    ["fitness", "athletics"]),
    ("Lawn Tennis Spring Cup",             "Open singles knockouts on the university asphalt court.",                                            "Sports",    ["athletics", "fitness"]),
    ("Aerobics & Zumba Morning Blast",     "High-energy cardio dance workout on the student pavilion to kick off Saturday.",                     "Sports",    ["fitness", "swimming"]),
    ("Handball Faculty Trophy",            "Fast-paced handball fixtures for men and women faculty squads.",                                     "Sports",    ["athletics", "fitness"]),
    ("Powerlifting & Strength Meet",       "Bench press, squat, and deadlift exhibition with strict form judging.",                              "Sports",    ["fitness", "athletics"]),
    ("Cycling Campus Tour",                "20KM group road ride exploring the scenic tea and coffee plantations.",                              "Sports",    ["fitness", "marathon"]),
    ("Field Hockey Friendly Match",        "DeKUT Warriors take on regional university champions in 11-a-side hockey.",                          "Sports",    ["athletics", "fitness"]),
    ("Sunset Stretch & Pilates",           "Core stability, flexibility, and breathing cooldown on the library lawn.",                          "Sports",    ["fitness", "swimming"]),

    # Additional Workshop (12)
    ("Docker & Containerization Lab",      "Containerize FastAPI backends and React frontends using Docker Compose.",                            "Workshop",  ["cloud", "hands-on", "web development"]),
    ("Prompt Engineering & LLMs",          "Practical prompting techniques, context retrieval, and model fine-tuning concepts.",                 "Workshop",  ["ai", "python", "advanced"]),
    ("Git & GitHub Professional Workflow", "Branching models, resolving merge conflicts, and conducting professional PR reviews.",               "Workshop",  ["training", "skills", "hands-on"]),
    ("Flutter for Cross-Platform Apps",    "State management, widgets, and clean architecture in Flutter.",                                      "Workshop",  ["mobile", "bootcamp", "hands-on"]),
    ("Arduino Robotics Hands-on",          "Assemble an obstacle-avoiding autonomous robot car from modular parts.",                             "Workshop",  ["iot", "hands-on", "training"]),
    ("REST API Development with FastAPI",  "Build asynchronous, production-ready REST backends with automatic OpenAPI docs.",                    "Workshop",  ["python", "web development", "advanced"]),
    ("Penetration Testing Laboratory",     "Ethical exploitation of vulnerable web apps in a controlled sandbox.",                               "Workshop",  ["cybersecurity", "hands-on", "advanced"]),
    ("Data Analysis with SQL & Postgres",  "Complex joins, window functions, and indexing strategies for high throughput.",                      "Workshop",  ["data science", "training", "skills"]),
    ("Microservices Architecture",         "Event-driven architectures, message queues, and decoupled service boundaries.",                     "Workshop",  ["cloud", "web development", "advanced"]),
    ("3D Printing & Rapid Prototyping",    "CAD modeling in Fusion 360, slicing, and 3D printing functional components.",                        "Workshop",  ["hands-on", "skills", "training"]),
    ("Scientific Computing with NumPy",    "Vectorized computation, matrix equations, and numerical simulations.",                               "Workshop",  ["python", "data science", "science"]),
    ("Kubernetes Deployment Workshop",     "Deploying containerized clusters, ingress controllers, and auto-scalers.",                           "Workshop",  ["cloud", "training", "advanced"]),

    # Additional Cultural (11)
    ("Traditional Drumming Intensive",     "Mastering the polyrhythmic drumming traditions of East Africa.",                                     "Cultural",  ["music", "heritage", "dance"]),
    ("Contemporary Fine Arts Studio",      "Oil on canvas and watercolor landscape painting workshop.",                                          "Cultural",  ["art", "hands-on"]),
    ("Scriptwriting for Stage and Screen", "Structuring acts, drafting sharp dialogue, and subtextual scene design.",                            "Cultural",  ["theatre", "film", "art"]),
    ("Campus Choir Spring Concert",        "Choral harmonies, classical arrangements, and Kenyan folk choral pieces.",                           "Cultural",  ["music", "community"]),
    ("African Literature Book Club",       "Discussing contemporary fiction and essays by emerging African authors.",                            "Cultural",  ["poetry", "heritage", "art"]),
    ("Swahili Spoken Word Showcase",       "Tuzo ya ushairi na tamthilia ya wanafunzi kwenye jukwaa kuu.",                                       "Cultural",  ["poetry", "heritage", "art"]),
    ("Documentary Film Pitch Session",     "Pitching short social-impact documentary projects to local media judges.",                           "Cultural",  ["film", "art"]),
    ("Urban Street Dance Battle",          "Hip hop, afrobeat, and breaking crews compete for the campus title.",                                "Cultural",  ["dance", "music"]),
    ("Heritage Cuisine Masterclass",       "Traditional indigenous Kenyan cuisine prep, fermentation, and seasoning.",                           "Cultural",  ["heritage", "community"]),
    ("Ceramics & Clay Sculpting Studio",   "Hand building, wheel throwing, and kiln glazing for beginners.",                                     "Cultural",  ["art", "hands-on"]),
    ("Campus Cultural Gala Night",         "Grand finale celebrating music, traditional dress, spoken word, and dance.",                         "Cultural",  ["heritage", "music", "dance", "fashion"]),

    # Additional Tech (12)
    ("GDSC Campus Solutions Challenge",    "Build tech solutions aligned with UN Sustainable Development Goals.",                                "Tech",      ["ai", "mobile", "web development"]),
    ("Autonomous Drone Navigation Talk",   "Computer vision tracking, optical flow, and PID stabilization in drones.",                           "Tech",      ["iot", "ai", "python"]),
    ("Network Defense & Packet Analysis",  "Wireshark deep packet inspection, firewall rules, and intrusion prevention.",                         "Tech",      ["cybersecurity", "cloud"]),
    ("High Performance Systems in Rust",   "Memory safety, zero-cost abstractions, and concurrency in systems programming.",                     "Tech",      ["advanced", "web development"]),
    ("Graph Neural Networks Overview",     "Analyzing social networks and molecular structures with PyTorch Geometric.",                         "Tech",      ["ai", "data science", "python"]),
    ("Serverless Architectures with AWS",  "Event-driven microservices using AWS Lambda, API Gateway, and DynamoDB.",                            "Tech",      ["cloud", "python"]),
    ("Frontend Performance Engineering",   "Optimizing bundle sizes, Core Web Vitals, and browser render pipelines.",                           "Tech",      ["javascript", "web development"]),
    ("Hardware Security & Reverse Eng",    "Firmware extraction, JTAG debugging, and side-channel vulnerability testing.",                       "Tech",      ["cybersecurity", "iot"]),
    ("Natural Language Processing with HF", "Transformer architectures, sentiment analysis, and tokenization in Python.",                        "Tech",      ["ai", "python", "data science"]),
    ("Robotics Buildathon: SumoBots",      "Design, build, and program autonomous combat robots for the ring.",                                  "Tech",      ["iot", "python", "hands-on"]),
    ("Big Data Processing with PySpark",   "Distributed DataFrame operations, streaming data, and cluster orchestration.",                       "Tech",      ["data science", "cloud", "python"]),
    ("DevFest Nyeri 2026",                 "Annual flagship Google Developer Groups summit featuring talks on AI, Cloud, and Web.",              "Tech",      ["ai", "cloud", "mobile", "web development"]),

    # Additional Career (11)
    ("Engineering Career Expo",            "Connect with top infrastructure, manufacturing, and automotive employers.",                          "Career",    ["internship", "networking"]),
    ("Consulting Case Interview Workshop", "Cracking profitability, market-entry, and strategy framework cases.",                                "Career",    ["interview", "skills"]),
    ("Health Sciences Career Colloquium",  "Opportunities in public health administration, clinical research, and pharma.",                      "Career",    ["mentorship", "internship"]),
    ("Software Salary & Offer Negotiation","Navigating compensation bands, equity grants, and international remote contracts.",                  "Career",    ["interview", "freelancing"]),
    ("Grant Writing & Research Funding",   "Crafting competitive grant proposals for university and external funding.",                          "Career",    ["mentorship", "skills"]),
    ("Corporate Networking Masterclass",   "Elevator pitches, strategic follow-ups, and building genuine professional allies.",                   "Career",    ["networking", "leadership"]),
    ("Venture Capital & Angel Funding",    "How early-stage African tech founders raise capital and structure term sheets.",                     "Career",    ["startup", "entrepreneurship"]),
    ("Freelance Developer Roundtable",     "Contracts, managing scope creep, and collecting international remittances.",                         "Career",    ["freelancing", "networking"]),
    ("LinkedIn Profile Teardown Live",     "Live profile reviews, headline optimization, and algorithm visibility tactics.",                     "Career",    ["resume", "networking"]),
    ("Graduate Trainee Pathways",          "Preparing for aptitude tests and assessment centers in banking and telcos.",                         "Career",    ["internship", "interview"]),
    ("Startup Incubator Demo Day",         "Student founders pitch validated prototypes to angel investors and mentors.",                        "Career",    ["startup", "entrepreneurship", "leadership"]),
]

# ── User Profiles ─────────────────────────────────────────────────────
# (username, full_name, email, role, interest_tags)
# Interest tags are chosen so each user maps to a clear subset of events.

USER_PROFILES = [
    # Tech-focused students (School of Computer Science & IT)
    ("alice_dev",     "Alice Wanjiku",     "alice@dekut.ac.ke",     "student",    "School of Computer Science & IT", ["tech", "python", "ai", "data science", "web development"]),
    ("bob_cyber",     "Bob Kimani",        "bob@dekut.ac.ke",       "student",    "School of Computer Science & IT", ["tech", "cybersecurity", "python", "cloud"]),
    ("carol_js",      "Carol Muthoni",     "carol@dekut.ac.ke",     "student",    "School of Computer Science & IT", ["tech", "javascript", "web development", "mobile"]),
    ("dave_data",     "Dave Ochieng",      "dave@dekut.ac.ke",      "student",    "School of Computer Science & IT", ["tech", "data science", "ai", "python", "research"]),
    ("kevin_cs",      "Kevin Macharia",    "kevin@dekut.ac.ke",     "student",    "School of Computer Science & IT", ["tech", "python", "ai", "cloud", "web development"]),
    ("samuel_cloud",  "Samuel Mutiso",     "samuel@dekut.ac.ke",    "student",    "School of Computer Science & IT", ["tech", "cloud", "cybersecurity", "web development"]),

    # Academic & Science students (School of Science & Applied Tech)
    ("eve_research",  "Eve Njeri",         "eve@dekut.ac.ke",       "student",    "School of Science & Applied Tech", ["academic", "research", "science", "thesis", "journal club"]),
    ("frank_math",    "Frank Mutua",       "frank@dekut.ac.ke",     "student",    "School of Science & Applied Tech", ["academic", "mathematics", "seminar", "study group"]),
    ("grace_env",     "Grace Akinyi",      "grace@dekut.ac.ke",     "student",    "School of Science & Applied Tech", ["academic", "science", "research", "data science"]),
    ("victor_physics","Victor Kibet",      "victor@dekut.ac.ke",    "student",    "School of Science & Applied Tech", ["academic", "science", "mathematics", "research"]),

    # Engineering students (School of Engineering)
    ("henry_sports",  "Henry Kipchoge",    "henry@dekut.ac.ke",     "student",    "School of Engineering", ["sports", "football", "athletics", "fitness", "marathon"]),
    ("dennis_mech",   "Dennis Kiprono",    "dennis@dekut.ac.ke",    "student",    "School of Engineering", ["tech", "iot", "science", "hands-on", "python"]),

    # Health & Nursing students (Health Sciences)
    ("irene_fit",     "Irene Wambui",      "irene@dekut.ac.ke",     "student",    "Health Sciences", ["sports", "fitness", "swimming", "volleyball"]),
    ("faith_nurse",   "Faith Chepkemoi",   "faith@dekut.ac.ke",     "student",    "Health Sciences", ["academic", "science", "research", "fitness", "community"]),

    # Cultural & Arts students (Cultural Society)
    ("james_art",     "James Mwangi",      "james@dekut.ac.ke",     "student",    "Cultural Society", ["cultural", "music", "art", "poetry", "film"]),
    ("karen_dance",   "Karen Nyambura",    "karen@dekut.ac.ke",     "student",    "Cultural Society", ["cultural", "dance", "heritage", "fashion", "theatre"]),

    # Career & Business students (School of Business)
    ("leo_career",    "Leo Otieno",        "leo@dekut.ac.ke",       "student",    "School of Business", ["career", "entrepreneurship", "startup", "leadership"]),
    ("mary_intern",   "Mary Wangari",      "mary@dekut.ac.ke",      "student",    "School of Business", ["career", "internship", "interview", "resume", "mentorship"]),
    ("brian_biz",     "Brian Kamau",       "brian@dekut.ac.ke",     "student",    "School of Business", ["career", "startup", "entrepreneurship", "networking"]),

    # Social & Mixed profiles
    ("nick_social",   "Nick Kamau",        "nick@dekut.ac.ke",      "student",    "Student Affairs & Sports", ["social", "networking", "community", "games"]),
    ("olivia_mix",    "Olivia Chebet",     "olivia@dekut.ac.ke",    "student",    "School of Business", ["social", "cultural", "music", "networking", "community"]),
    ("peter_all",     "Peter Njoroge",     "peter@dekut.ac.ke",     "student",    "School of Computer Science & IT", ["tech", "career", "entrepreneurship", "python", "startup"]),

    # Organizers
    ("org_tech",      "Tech Club DeKUT",   "techclub@dekut.ac.ke",  "organizer",  "School of Computer Science & IT", ["tech", "python", "ai", "hackathon"]),
    ("org_sports",    "Sports Council",    "sports@dekut.ac.ke",    "organizer",  "Student Affairs & Sports", ["sports", "football", "athletics"]),
    ("org_culture",   "Cultural Society",  "culture@dekut.ac.ke",   "organizer",  "Cultural Society", ["cultural", "music", "dance", "art"]),
    ("admin_dekut",   "Admin DEEMS",       "admin@dekut.ac.ke",     "admin",      "School of Computer Science & IT", ["academic", "career", "tech"]),
]

DEFAULT_PASSWORD = "Password123"


def compute_relevance(user_tags: set, event_category: str, event_tags: set) -> bool:
    """
    Determine if an event is relevant to a user based on tag overlap.
    An event is 'relevant' if:
      - The event's category (lowered) is in the user's interest tags, OR
      - At least 2 of the event's tags overlap with the user's tags.
    """
    if event_category.lower() in user_tags:
        return True
    overlap = user_tags & event_tags
    return len(overlap) >= 2


def main():
    # Recreate all tables (dev-only — wipes existing data)
    print("Dropping and recreating all tables...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    try:
        # ── Create Users ──────────────────────────────────────────────
        print(f"Creating {len(USER_PROFILES)} users...")
        users = {}
        for username, full_name, email, role, dept, _ in USER_PROFILES:
            user = User(
                id=uuid.uuid4(),
                email=email,
                username=username,
                hashed_password=hash_password(DEFAULT_PASSWORD),
                full_name=full_name,
                role=role,
                department=dept,
            )
            db.add(user)
            users[username] = user

        db.flush()  # Get IDs assigned

        # ── Create User Interests ─────────────────────────────────────
        print("Setting user interest tags...")
        user_tag_sets = {}
        for username, _, _, _, _, interest_tags in USER_PROFILES:
            tag_set = set()
            for tag in interest_tags:
                interest = UserInterest(
                    user_id=users[username].id,
                    interest_tag=tag.lower(),
                    weight=1.0,
                )
                db.add(interest)
                tag_set.add(tag.lower())
            user_tag_sets[username] = tag_set

        db.flush()

        # ── Create Events ─────────────────────────────────────────────
        print(f"Creating {len(EVENT_TEMPLATES)} events...")
        now = datetime.now(timezone.utc)
        events = []
        event_meta = {}  # event_id -> (category, tag_set)

        # Pick organizers and departments by category
        cat_organizers = {
            "Academic":  "admin_dekut",
            "Social":    "org_culture",
            "Sports":    "org_sports",
            "Workshop":  "org_tech",
            "Cultural":  "org_culture",
            "Tech":      "org_tech",
            "Career":    "admin_dekut",
        }

        cat_departments = {
            "Academic":  "School of Science & Applied Tech",
            "Social":    "Student Affairs & Sports",
            "Sports":    "Student Affairs & Sports",
            "Workshop":  "School of Computer Science & IT",
            "Cultural":  "Cultural Society",
            "Tech":      "School of Computer Science & IT",
            "Career":    "School of Business",
        }

        for i, (title, description, category, extra_tags) in enumerate(EVENT_TEMPLATES):
            # Spread events over the next 60 days
            start_offset = timedelta(days=random.randint(1, 60), hours=random.randint(8, 18))
            start_time = now + start_offset
            end_time = start_time + timedelta(hours=random.choice([2, 3, 4, 6, 8]))

            tags_str = ",".join(extra_tags)
            organizer_username = cat_organizers.get(category, "admin_dekut")
            dept_name = cat_departments.get(category, "School of Computer Science & IT")

            event = Event(
                id=uuid.uuid4(),
                title=title,
                description=description,
                category=category,
                department=dept_name,
                location=random.choice(LOCATIONS),
                start_time=start_time,
                end_time=end_time,
                max_attendees=random.choice([None, 30, 50, 100, 200]),
                tags=tags_str,
                organizer_id=users[organizer_username].id,
                is_published=True,
            )
            db.add(event)
            events.append(event)
            event_meta[event.id] = (category, set(t.lower() for t in extra_tags))

        db.flush()

        # ── Create RSVPs ──────────────────────────────────────────────
        print("Creating RSVPs based on interest correlations...")
        rsvp_count = 0
        ground_truth = {}  # username -> list of event IDs that are relevant

        student_profiles = [
            (username, tags) for username, _, _, role, _, tags in USER_PROFILES
            if role == "student"
        ]

        for username, interest_tags in student_profiles:
            tag_set = set(t.lower() for t in interest_tags)
            relevant_event_ids = []

            for event in events:
                cat, etags = event_meta[event.id]
                if compute_relevance(tag_set, cat, etags):
                    relevant_event_ids.append(str(event.id))

            # RSVP to ~60-80% of relevant events (simulates realistic behaviour)
            rsvp_events = random.sample(
                relevant_event_ids,
                k=min(len(relevant_event_ids), max(3, int(len(relevant_event_ids) * random.uniform(0.6, 0.8)))),
            )

            for eid_str in rsvp_events:
                rsvp = RSVP(
                    user_id=users[username].id,
                    event_id=uuid.UUID(eid_str),
                    status="confirmed",
                )
                db.add(rsvp)
                rsvp_count += 1

            # Also add 1-2 RSVPs to random non-relevant events (noise)
            non_relevant = [str(e.id) for e in events if str(e.id) not in relevant_event_ids]
            noise_rsvps = random.sample(non_relevant, k=min(2, len(non_relevant)))
            for eid_str in noise_rsvps:
                rsvp = RSVP(
                    user_id=users[username].id,
                    event_id=uuid.UUID(eid_str),
                    status="confirmed",
                )
                db.add(rsvp)
                rsvp_count += 1

            ground_truth[username] = relevant_event_ids

        db.commit()

        # ── Save Ground Truth ─────────────────────────────────────────
        gt_path = "seed_ground_truth.json"
        with open(gt_path, "w") as f:
            json.dump(ground_truth, f, indent=2)

        print(f"\n[OK] Seed complete!")
        print(f"   Users:    {len(users)}")
        print(f"   Events:   {len(events)}")
        print(f"   RSVPs:    {rsvp_count}")
        print(f"   Ground truth saved to: {gt_path}")
        print(f"\n   All users have password: {DEFAULT_PASSWORD}")
        print(f"   Example login: alice@dekut.ac.ke / {DEFAULT_PASSWORD}")

    except Exception as e:
        db.rollback()
        print(f"[FAIL] Seed failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
