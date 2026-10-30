"""Realistic mock data for Common Ground offline testing and Qloo fallback.

Contains curated venues for at least two major global cultural travel destinations
(Lisbon and Tokyo) spanning all 6 required categories:
- hotel
- restaurant
- cafe
- bar
- attraction
- shop

Includes realistic taste tags, price levels, descriptions, and dynamic affinity scoring
that genuinely varies based on user taste signals/favorites.
"""

from typing import List, Dict, Any
import hashlib


# Curated catalog of venues organized by city and category
MOCK_CITIES_DATA: Dict[str, Dict[str, List[Dict[str, Any]]]] = {
    "lisbon": {
        "hotel": [
            {
                "id": "lis-ht-01",
                "name": "Santa Clara 1728",
                "category": "hotel",
                "location": "Lisbon, Alfama",
                "price_level": "$$$$",
                "tags": ["minimalism", "serene", "architectural", "silent-luxury", "heritage"],
                "description": "Quiet, 18th-century palace restored with pale limestone and warm wood in historic Alfama.",
                "address": "Campo de Santa Clara 128, 1100-473 Lisboa",
            },
            {
                "id": "lis-ht-02",
                "name": "The Lumiares Hotel & Spa",
                "category": "hotel",
                "location": "Lisbon, Bairro Alto",
                "price_level": "$$$",
                "tags": ["boutique", "rooftop-views", "design", "vibrant", "artistic"],
                "description": "Stylish boutique hotel celebrating Portuguese craftsmanship with a panoramic rooftop terrace.",
                "address": "R. de São Pedro de Alcântara 35, 1250-237 Lisboa",
            },
            {
                "id": "lis-ht-03",
                "name": "Casa Fortunato",
                "category": "hotel",
                "location": "Lisbon, Amoreiras",
                "price_level": "$$$",
                "tags": ["eclectic", "artsy", "family-run", "cozy", "design-lover"],
                "description": "Intimate 9-room townhouse filled with curated contemporary art and mid-century furniture.",
                "address": "R. da Artilharia 1 20, 1250-038 Lisboa",
            },
        ],
        "restaurant": [
            {
                "id": "lis-rs-01",
                "name": "Prado",
                "category": "restaurant",
                "location": "Lisbon, Sé",
                "price_level": "$$$",
                "tags": ["farm-to-table", "natural-wine", "seasonal", "contemporary", "creative"],
                "description": "Botanical farm-to-table dining spotlighting regional Portuguese ingredients under hanging ivy.",
                "address": "Tv. Pedras Negras 2, 1100-404 Lisboa",
            },
            {
                "id": "lis-rs-02",
                "name": "Ramiro",
                "category": "restaurant",
                "location": "Lisbon, Intendente",
                "price_level": "$$",
                "tags": ["traditional", "seafood", "bustling", "classic", "iconic"],
                "description": "Legendary beer hall serving pristine scarlet prawns, clams in garlic, and prego steak sandwiches.",
                "address": "Av. Almirante Reis 1, 1150-018 Lisboa",
            },
            {
                "id": "lis-rs-03",
                "name": "Taberna do Calhau",
                "category": "restaurant",
                "location": "Lisbon, Mouraria",
                "price_level": "$$",
                "tags": ["alentejo", "craft-cooking", "authentic", "natural-wine", "soulful"],
                "description": "Chef Leopoldo's rustic Alentejo cooking paired with rare low-intervention amphora wines.",
                "address": "Largo das Olarias 23, 1100-376 Lisboa",
            },
        ],
        "cafe": [
            {
                "id": "lis-cf-01",
                "name": "Fábrica Coffee Roasters",
                "category": "cafe",
                "location": "Lisbon, Baixa",
                "price_level": "$",
                "tags": ["specialty-coffee", "pour-over", "roastery", "minimalist", "urban"],
                "description": "Pioneering Lisbon specialty coffee roastery with single-origin pour-overs and industrial aesthetic.",
                "address": "R. das Portas de Santo Antão 136, 1150-269 Lisboa",
            },
            {
                "id": "lis-cf-02",
                "name": "Hello, Kristof",
                "category": "cafe",
                "location": "Lisbon, Poço dos Negros",
                "price_level": "$",
                "tags": ["indie-magazines", "scandinavian", "flat-white", "editorial", "quiet"],
                "description": "Espresso bar and indie magazine library serving clean Scandinavian roasts and avocado tartines.",
                "address": "R. do Poço dos Negros 103, 1200-337 Lisboa",
            },
            {
                "id": "lis-cf-03",
                "name": "Bettina & Niccolò Corallo",
                "category": "cafe",
                "location": "Lisbon, Príncipe Real",
                "price_level": "$$",
                "tags": ["single-origin-chocolate", "pure-espresso", "artisanal", "purist", "heritage"],
                "description": "Single-estate São Tomé chocolate shop and espresso tasting room tucked into Príncipe Real.",
                "address": "R. da Escola Politécnica 4, 1250-102 Lisboa",
            },
        ],
        "bar": [
            {
                "id": "lis-br-01",
                "name": "Vino Vero",
                "category": "bar",
                "location": "Lisbon, Graça",
                "price_level": "$$",
                "tags": ["natural-wine", "biodynamic", "intimate", "neighborhood", "terrace"],
                "description": "Venetian outpost in Graça pouring rare skin-contact orange wines and spontaneous pet-nats.",
                "address": "Tv. do Monte 30, 1170-265 Lisboa",
            },
            {
                "id": "lis-br-02",
                "name": "Red Frog Speakeasy",
                "category": "bar",
                "location": "Lisbon, Avenida da Liberdade",
                "price_level": "$$$",
                "tags": ["cocktail-craft", "speakeasy", "experimental", "dim-lit", "avant-garde"],
                "description": "World-class subterranean speakeasy serving culinary-inspired boundary-pushing cocktails.",
                "address": "Praça da Alegria 66b, 1250-004 Lisboa",
            },
            {
                "id": "lis-br-03",
                "name": "Largo Lounge Bar",
                "category": "bar",
                "location": "Lisbon, Intendente",
                "price_level": "$",
                "tags": ["arts-hub", "bohemian", "alfresco", "music", "relaxed"],
                "description": "Artsy open-air courtyard in a reclaimed Intendente warehouse hosting acoustic music and spritzes.",
                "address": "Largo do Intendente Pina Manique 19, 1100-285 Lisboa",
            },
        ],
        "attraction": [
            {
                "id": "lis-at-01",
                "name": "MAAT (Museum of Art, Architecture & Technology)",
                "category": "attraction",
                "location": "Lisbon, Belém",
                "price_level": "$$",
                "tags": ["contemporary-art", "architecture", "waterfront", "futuristic", "design"],
                "description": "Undulating ceramic-tiled pavilion on the Tagus riverbank featuring radical global installations.",
                "address": "Av. Brasília, 1300-598 Lisboa",
            },
            {
                "id": "lis-at-02",
                "name": "Calouste Gulbenkian Foundation & Gardens",
                "category": "attraction",
                "location": "Lisbon, Praça de Espanha",
                "price_level": "$$",
                "tags": ["brutalism", "lush-gardens", "art-collection", "modernist", "oasis"],
                "description": "Concrete modernist sanctuary blending world-class art collections with wild botanical groves.",
                "address": "Av. de Berna 45A, 1067-001 Lisboa",
            },
            {
                "id": "lis-at-03",
                "name": "Miradouro de Santa Catarina & Adamastor",
                "category": "attraction",
                "location": "Lisbon, Santa Catarina",
                "price_level": "$",
                "tags": ["sunset", "panoramic-views", "social", "buskers", "river-views"],
                "description": "Beloved sunset hill terrace overlooking the 25 de Abril Bridge with street musicians.",
                "address": "R. de Santa Catarina, 1200-403 Lisboa",
            },
        ],
        "shop": [
            {
                "id": "lis-sh-01",
                "name": "Under the Cover",
                "category": "shop",
                "location": "Lisbon, São Sebastião",
                "price_level": "$$",
                "tags": ["independent-print", "art-books", "magazines", "editorial", "typography"],
                "description": "Curated indie magazine boutique facing the Gulbenkian park with rare design periodicals.",
                "address": "R. Marquês Sá da Bandeira 88B, 1070-070 Lisboa",
            },
            {
                "id": "lis-sh-02",
                "name": "A Vida Portuguesa",
                "category": "shop",
                "location": "Lisbon, Chiado",
                "price_level": "$$",
                "tags": ["heritage-goods", "vintage-packaging", "ceramics", "design", "craft"],
                "description": "Nostalgic marketplace reviving classic Portuguese typography, soaps, ceramics, and textiles.",
                "address": "R. Anchieta 11, 1200-087 Lisboa",
            },
            {
                "id": "lis-sh-03",
                "name": "Flur Discos",
                "category": "shop",
                "location": "Lisbon, Santa Apolónia",
                "price_level": "$$",
                "tags": ["vinyl-records", "electronic", "indie", "ambient", "crate-digging"],
                "description": "Premier vinyl shop by the river docks curating experimental ambient, house, techno, and jazz.",
                "address": "Av. Infante Dom Henrique 19, 1950-406 Lisboa",
            },
        ],
    },
    "tokyo": {
        "hotel": [
            {
                "id": "tyo-ht-01",
                "name": "TRUNK (HOTEL) Yoyogi Park",
                "category": "hotel",
                "location": "Tokyo, Tomigaya",
                "price_level": "$$$$",
                "tags": ["boutique", "park-views", "minimalist", "rooftop-pool", "design"],
                "description": "Serene retreat crafted in washed concrete and native wood facing Yoyogi Park.",
                "address": "1-15-2 Tomigaya, Shibuya, Tokyo 151-0063",
            },
            {
                "id": "tyo-ht-02",
                "name": "K5 Tokyo",
                "category": "hotel",
                "location": "Tokyo, Nihombashi",
                "price_level": "$$$",
                "tags": ["revitalized-heritage", "botanical", "scandi-japanese", "cocktail-bar", "hip"],
                "description": "Micro-hotel in a 1920s bank converted with Swedish design sensibilities and indoor greenery.",
                "address": "3-10-1 Nihombashi Kabutocho, Chuo, Tokyo 103-0026",
            },
            {
                "id": "tyo-ht-03",
                "name": "Hoshinoya Tokyo",
                "category": "hotel",
                "location": "Tokyo, Otemachi",
                "price_level": "$$$$",
                "tags": ["modern-ryokan", "luxury", "onsen", "tatami", "tranquil"],
                "description": "A vertical luxury ryokan in the financial district with natural hot springs and cedar aromas.",
                "address": "1-9-1 Otemachi, Chiyoda, Tokyo 100-0004",
            },
        ],
        "restaurant": [
            {
                "id": "tyo-rs-01",
                "name": "Den",
                "category": "restaurant",
                "location": "Tokyo, Jingumae",
                "price_level": "$$$$",
                "tags": ["modern-kaiseki", "playful", "michelin", "hospitality", "seasonal"],
                "description": "Inventive kaiseki dining by Chef Zaiyu Hasegawa blending refined technique with joyful surprises.",
                "address": "2-3-18 Jingumae, Shibuya, Tokyo 150-0001",
            },
            {
                "id": "tyo-rs-02",
                "name": "Butagumi",
                "category": "restaurant",
                "location": "Tokyo, Nishi-Azabu",
                "price_level": "$$",
                "tags": ["tonkatsu", "craft-pork", "heritage-house", "artisanal", "comfort-food"],
                "description": "Specialty tonkatsu served inside a restored pre-war wooden house with curated heirloom cuts.",
                "address": "2-24-9 Nishi-Azabu, Minato, Tokyo 106-0031",
            },
            {
                "id": "tyo-rs-03",
                "name": "Narisawa",
                "category": "restaurant",
                "location": "Tokyo, Minami Aoyama",
                "price_level": "$$$$",
                "tags": ["satoyama-cuisine", "sustainable", "avant-garde", "nature-inspired", "tasting-menu"],
                "description": "Chef Yoshihiro Narisawa's pioneering ode to Japan's natural ecology and forest gastronomy.",
                "address": "2-6-15 Minami Aoyama, Minato, Tokyo 107-0062",
            },
        ],
        "cafe": [
            {
                "id": "tyo-cf-01",
                "name": "Fuglen Tokyo",
                "category": "cafe",
                "location": "Tokyo, Tomigaya",
                "price_level": "$",
                "tags": ["scandinavian-roast", "mid-century", "cocktails", "relaxed", "neighborhood"],
                "description": "Oslo-born cafe and vintage furniture lounge serving clean Nordic roasts by day, craft cocktails by night.",
                "address": "1-39-6 Tomigaya, Shibuya, Tokyo 151-0063",
            },
            {
                "id": "tyo-cf-02",
                "name": "Koffee Mameya Kakeru",
                "category": "cafe",
                "location": "Tokyo, Kiyosumi-Shirakawa",
                "price_level": "$$$",
                "tags": ["coffee-omakase", "single-origin", "minimalist", "gastronomic", "precise"],
                "description": "The world's first fine-dining coffee tasting counter in Tokyo's quiet roastery neighborhood.",
                "address": "2-16-14 Hirano, Koto, Tokyo 135-0023",
            },
            {
                "id": "tyo-cf-03",
                "name": "Chatei Hatou",
                "category": "cafe",
                "location": "Tokyo, Shibuya",
                "price_level": "$$",
                "tags": ["kissaten", "slow-drip", "charcoal-roast", "ceremony", "vintage-porcelain"],
                "description": "Atmospheric kissaten legendary for slow flannel drip coffee poured into custom antique ceramics.",
                "address": "1-15-19 Shibuya, Tokyo 150-0002",
            },
        ],
        "bar": [
            {
                "id": "tyo-br-01",
                "name": "Bar Trench",
                "category": "bar",
                "location": "Tokyo, Ebisu",
                "price_level": "$$$",
                "tags": ["herbal-spirits", "absinthe", "craft-cocktails", "intimate", "classic"],
                "description": "Cozy cocktail sanctuary celebrated for rare herbal liqueurs, house bitters, and tailored service.",
                "address": "1-5-8 Ebisunishi, Shibuya, Tokyo 150-0021",
            },
            {
                "id": "tyo-br-02",
                "name": "Lion Kissaten & Sound Bar",
                "category": "bar",
                "location": "Tokyo, Dogenzaka",
                "price_level": "$",
                "tags": ["audiophile", "classical-music", "silent-listening", "custom-horn-speakers", "historic"],
                "description": "Showpiece audiophile venue with colossal custom horn speakers and a reverent listening hall.",
                "address": "2-19-13 Dogenzaka, Shibuya, Tokyo 150-0043",
            },
            {
                "id": "tyo-br-03",
                "name": "Ahiru Store",
                "category": "bar",
                "location": "Tokyo, Tomigaya",
                "price_level": "$$",
                "tags": ["natural-wine", "casual", "sourdough-bakery", "brother-sister-run", "cozy"],
                "description": "Intimate natural wine bistro and bakery serving crusty sourdough and seasonal small plates.",
                "address": "1-22-5 Tomigaya, Shibuya, Tokyo 151-0063",
            },
        ],
        "attraction": [
            {
                "id": "tyo-at-01",
                "name": "Mori Art Museum",
                "category": "attraction",
                "location": "Tokyo, Roppongi",
                "price_level": "$$",
                "tags": ["contemporary-art", "skyline-views", "cutting-edge", "global-exhibitions"],
                "description": "53rd-floor modern art institution presenting international contemporary visions over Tokyo skyline.",
                "address": "6-10-1 Roppongi, Minato, Tokyo 106-6150",
            },
            {
                "id": "tyo-at-02",
                "name": "Nezu Museum",
                "category": "attraction",
                "location": "Tokyo, Minami Aoyama",
                "price_level": "$$",
                "tags": ["japanese-gardens", "kengo-kuma", "bamboo-walkway", "traditional-art", "tea-house"],
                "description": "Kengo Kuma designed museum hosting pre-modern Asian artifacts with an expansive stroll garden.",
                "address": "6-5-1 Minami Aoyama, Minato, Tokyo 107-0062",
            },
            {
                "id": "tyo-at-03",
                "name": "Meiji Jingu Forest Shrine",
                "category": "attraction",
                "location": "Tokyo, Yoyogi",
                "price_level": "$",
                "tags": ["sacred-forest", "shinto-architecture", "peaceful", "torii-gate", "nature"],
                "description": "Centuries-old man-made sacred forest wrapping the imperial Shinto shrine in central Shibuya.",
                "address": "1-1 Yoyogikamizonocho, Shibuya, Tokyo 151-8557",
            },
        ],
        "shop": [
            {
                "id": "tyo-sh-01",
                "name": "Daikanyama T-Site (Tsutaya Books)",
                "category": "shop",
                "location": "Tokyo, Daikanyama",
                "price_level": "$$",
                "tags": ["architecture", "rare-art-books", "vintage-vinyl", "stationery", "design-hub"],
                "description": "Award-winning complex of three interconnected architectural pavilions celebrating print and music.",
                "address": "17-5 Sarugakucho, Shibuya, Tokyo 150-0033",
            },
            {
                "id": "tyo-sh-02",
                "name": "Visvim / F.I.L. Tokyo",
                "category": "shop",
                "location": "Tokyo, Omotesando",
                "price_level": "$$$$",
                "tags": ["heritage-textiles", "indigo-dye", "craftsmanship", "curated-menswear", "architectural"],
                "description": "Hiroki Nakamura's flagship blending vintage Americana, Japanese indigo dyeing, and artisanal footwear.",
                "address": "5-5-25 Minami Aoyama, Minato, Tokyo 107-0062",
            },
            {
                "id": "tyo-sh-03",
                "name": "Tokyu Hands Shibuya",
                "category": "shop",
                "location": "Tokyo, Shibuya",
                "price_level": "$$",
                "tags": ["craft-supplies", "stationery", "diy", "creative-tools", "japanese-gadgets"],
                "description": "Multi-floor creative emporium filled with Japanese pens, leathercrafting tools, and design hardware.",
                "address": "12-18 Udagawacho, Shibuya, Tokyo 150-0042",
            },
        ],
    },
    "delhi": {
        "hotel": [
            {
                "id": "del-ht-01",
                "name": "The Imperial New Delhi",
                "category": "hotel",
                "location": "Delhi, Janpath",
                "price_level": "$$$$",
                "tags": ["heritage", "art-deco", "historic-luxury", "colonial-architecture", "botanical-gardens"],
                "description": "Legendary 1930s Art Deco luxury hotel surrounded by royal palms, housing Museum-grade colonial art.",
                "address": "Janpath, Connaught Place, New Delhi 110001",
            },
            {
                "id": "del-ht-02",
                "name": "The Lodhi",
                "category": "hotel",
                "location": "Delhi, Lodhi Road",
                "price_level": "$$$$",
                "tags": ["minimalist", "modern-luxury", "plunge-pool", "art-collection", "serene"],
                "description": "Sophisticated urban oasis designed by Kerry Hill with private plunge pools, sandstone arches, and manicured lawns.",
                "address": "Lodhi Rd, CGO Complex, Pragati Vihar, New Delhi 110003",
            },
            {
                "id": "del-ht-03",
                "name": "Haveli Dharampura",
                "category": "hotel",
                "location": "Delhi, Chandni Chowk",
                "price_level": "$$$",
                "tags": ["mughal-heritage", "restored-mansion", "rooftop-views", "cultural", "boutique"],
                "description": "UNESCO-recognized restored 19th-century Mughal haveli inside Old Delhi with classical Kathak performances.",
                "address": "2293, Gali Guliyan, Dharampura, Chandni Chowk, Old Delhi 110006",
            },
        ],
        "restaurant": [
            {
                "id": "del-rs-01",
                "name": "Indian Accent",
                "category": "restaurant",
                "location": "Delhi, Lodhi Road",
                "price_level": "$$$$",
                "tags": ["progressive-indian", "tasting-menu", "inventive", "contemporary", "fine-dining"],
                "description": "Chef Manish Mehrotra's globally celebrated progressive Indian dining reimagining nostalgic regional flavors.",
                "address": "The Lodhi, Lodhi Rd, New Delhi 110003",
            },
            {
                "id": "del-rs-02",
                "name": "Bukhara",
                "category": "restaurant",
                "location": "Delhi, Chanakyapuri",
                "price_level": "$$$$",
                "tags": ["traditional", "tandoori", "clay-oven", "dal-bukhara", "rustic-luxury"],
                "description": "Iconic northwest frontier dining celebrated worldwide for 18-hour slow-cooked Dal Bukhara and clay tandoor roasts.",
                "address": "ITC Maurya, Sardar Patel Marg, Diplomatic Enclave, New Delhi 110021",
            },
            {
                "id": "del-rs-03",
                "name": "Carnatic Cafe",
                "category": "restaurant",
                "location": "Delhi, Greater Kailash",
                "price_level": "$$",
                "tags": ["south-indian", "dosa", "vegetarian", "pure-ghee", "comfort-food"],
                "description": "Beloved Karnataka kitchen renowned for fluffy Malleshwaram 18th Cross dosas crisped in pure white butter.",
                "address": "M-21, M Block Market, Greater Kailash II, New Delhi 110048",
            },
        ],
        "cafe": [
            {
                "id": "del-cf-01",
                "name": "Blue Tokai Coffee Roasters",
                "category": "cafe",
                "location": "Delhi, Champa Gali",
                "price_level": "$",
                "tags": ["specialty-coffee", "pour-over", "roastery", "artisanal", "indie-courtyard"],
                "description": "Pioneering Indian single-estate roastery nestled in an artisanal alleyway with pour-over brew bar.",
                "address": "Khasra 258, Lane 3, Westend Marg, Saidulajab, New Delhi 110030",
            },
            {
                "id": "del-cf-02",
                "name": "Caara at Ogaan",
                "category": "cafe",
                "location": "Delhi, Malcha Marg",
                "price_level": "$$",
                "tags": ["farm-fresh", "european-cafe", "pastries", "quaint", "scandinavian-clean"],
                "description": "Sunlit boutique cafe inside a designer fashion house serving chemical-free farm-to-table toasts and clean sourdough.",
                "address": "4 & 5, Malcha Marg Shopping Centre, Diplomatic Enclave, New Delhi 110021",
            },
            {
                "id": "del-cf-03",
                "name": "Perch Wine & Coffee Bar",
                "category": "cafe",
                "location": "Delhi, Khan Market",
                "price_level": "$$",
                "tags": ["specialty-coffee", "wine-bar", "minimalist-wood", "conversational", "relaxed"],
                "description": "Breezy multi-level wooden loft in Khan Market celebrated for Vietnamese pour-overs, cold brews, and natural wines.",
                "address": "71, Khan Market, Rabindra Nagar, New Delhi 110003",
            },
        ],
        "bar": [
            {
                "id": "del-br-01",
                "name": "Sidecar",
                "category": "bar",
                "location": "Delhi, Greater Kailash",
                "price_level": "$$$",
                "tags": ["craft-cocktails", "speakeasy", "award-winning", "artisanal-spirits", "book-lounge"],
                "description": "Consistently ranked among the World's 50 Best Bars, featuring artisanal bitters, bookshop decor, and tailored hospitality.",
                "address": "M-29, First Floor, M Block Market, Greater Kailash II, New Delhi 110048",
            },
            {
                "id": "del-br-02",
                "name": "PCO (Pass Code Only)",
                "category": "bar",
                "location": "Delhi, Vasant Vihar",
                "price_level": "$$$",
                "tags": ["speakeasy", "bespoke-cocktails", "hidden-phone-booth", "dim-lit", "classic"],
                "description": "India's first speakeasy accessible only via a secret rotating keypad code hidden inside an antique phone booth.",
                "address": "D-4, Block D, Vasant Vihar, New Delhi 110057",
            },
            {
                "id": "del-br-03",
                "name": "The Piano Man Jazz Club",
                "category": "bar",
                "location": "Delhi, Safdarjung Enclave",
                "price_level": "$$",
                "tags": ["live-jazz", "audiophile", "brick-interiors", "cocktails", "music-hub"],
                "description": "Revered music sanctum with exposed brick, a grand piano, custom acoustics, and nightly live jazz recitals.",
                "address": "7/22, Ground Floor, Safdarjung Enclave Market, New Delhi 110029",
            },
        ],
        "attraction": [
            {
                "id": "del-at-01",
                "name": "Humayun's Tomb & Sunder Nursery",
                "category": "attraction",
                "location": "Delhi, Nizamuddin",
                "price_level": "$",
                "tags": ["mughal-architecture", "unesco-heritage", "persian-gardens", "monumental", "botanical"],
                "description": "16th-century red sandstone Mughal masterpiece surrounded by pristine Persian charbagh gardens and 90-acre heritage arboretum.",
                "address": "Hazrat Nizamuddin Aulia, New Delhi 110013",
            },
            {
                "id": "del-at-02",
                "name": "National Gallery of Modern Art (NGMA)",
                "category": "attraction",
                "location": "Delhi, India Gate",
                "price_level": "$",
                "tags": ["contemporary-art", "sculpture-garden", "modernist", "historic-palace", "visual-arts"],
                "description": "Premier national art institution housed in the former Jaipur House showcasing Amrita Sher-Gil, Tagore, and modern sculptures.",
                "address": "Jaipur House, Shershah Rd, India Gate, New Delhi 110003",
            },
            {
                "id": "del-at-03",
                "name": "Kiran Nadar Museum of Art (KNMA)",
                "category": "attraction",
                "location": "Delhi, Saket",
                "price_level": "$",
                "tags": ["contemporary-art", "cutting-edge", "avant-garde", "installations", "private-collection"],
                "description": "India's landmark private modern art museum curating cutting-edge post-independence and contemporary South Asian art.",
                "address": "145, DLF South Court Mall, Saket, New Delhi 110017",
            },
        ],
        "shop": [
            {
                "id": "del-sh-01",
                "name": "Khan Market Bookshops (Bahrisons & Faqir Chand)",
                "category": "shop",
                "location": "Delhi, Khan Market",
                "price_level": "$$",
                "tags": ["independent-books", "literary-heritage", "art-books", "historic", "curated-print"],
                "description": "Legendary post-1947 indie bookshops with floor-to-ceiling volumes of South Asian literature, art monographs, and poetry.",
                "address": "Khan Market, Rabindra Nagar, New Delhi 110003",
            },
            {
                "id": "del-sh-02",
                "name": "Fabindia Home Experience Center",
                "category": "shop",
                "location": "Delhi, Lajpat Nagar",
                "price_level": "$$",
                "tags": ["handloom-textiles", "artisan-crafts", "organic", "indian-heritage", "sustainable"],
                "description": "Multi-story experiential craft emporium spotlighting regional hand-block printing, indigenous textiles, and wooden decor.",
                "address": "14, N Block Market, Greater Kailash I, New Delhi 110048",
            },
            {
                "id": "del-sh-03",
                "name": "Dilli Haat Crafts Village",
                "category": "shop",
                "location": "Delhi, INA",
                "price_level": "$",
                "tags": ["indigenous-craft", "handicrafts", "artisan-market", "textiles", "pottery"],
                "description": "Open-air thatched-roof cultural marketplace hosting rotating master artisans from all 28 states of India.",
                "address": "Sri Aurobindo Marg, Dilli Haat, Kidwai Nagar West, New Delhi 110023",
            },
        ],
    },
}


# Mock cultural entities for the search_entity function
MOCK_SEARCH_ENTITIES = [
    {"id": "urn:entity:music:burial", "name": "Burial", "type": "artist", "category": "music", "tags": ["electronic", "ambient", "dubstep", "moody"]},
    {"id": "urn:entity:music:ryuichi_sakamoto", "name": "Ryuichi Sakamoto", "type": "artist", "category": "music", "tags": ["neoclassical", "ambient", "film-score", "electronic"]},
    {"id": "urn:entity:music:phoebe_bridgers", "name": "Phoebe Bridgers", "type": "artist", "category": "music", "tags": ["indie-rock", "folk", "sad-girl", "melodic"]},
    {"id": "urn:entity:dining:natural_wine", "name": "Natural Wine", "type": "concept", "category": "beverage", "tags": ["pet-nat", "biodynamic", "skin-contact", "low-intervention"]},
    {"id": "urn:entity:dining:specialty_coffee", "name": "Specialty Coffee", "type": "concept", "category": "beverage", "tags": ["single-origin", "pour-over", "roaster", "third-wave"]},
    {"id": "urn:entity:brand:aesop", "name": "Aesop", "type": "brand", "category": "lifestyle", "tags": ["botanical", "architectural-retail", "scent", "minimalist"]},
    {"id": "urn:entity:art:james_turrell", "name": "James Turrell", "type": "artist", "category": "art", "tags": ["light-space", "monumental", "perception", "minimalism"]},
    {"id": "urn:entity:cinema:a24", "name": "A24", "type": "brand", "category": "film", "tags": ["indie-film", "editorial", "art-house", "auteur"]},
]


def calculate_mock_affinity(candidate_tags: List[str], candidate_name: str, signals: List[str]) -> float:
    """Calculates a realistic, varied affinity score (0.0 to 1.0) based on signal overlap.

    - Overlapping keywords between signals and venue tags push score higher.
    - Deterministic hashing guarantees consistent results for identical inputs.
    - Scores vary distinctly when different taste signals are provided.
    """
    if not signals:
        # Base neutral score between 0.60 and 0.75
        h = int(hashlib.md5(candidate_name.encode()).hexdigest(), 16)
        return round(0.60 + (h % 15) / 100.0, 2)

    # Normalize taste signals and candidate tags for case-insensitive matching
    normalized_signals = [
        (s.get("name", "") if isinstance(s, dict) else str(s)).lower().strip()
        for s in signals
    ]
    normalized_tags = [t.lower().replace("-", " ") for t in candidate_tags]

    matches = 0
    total_checks = len(signals)

    for signal in normalized_signals:
        signal_words = signal.split()
        for tag in normalized_tags:
            # Check for direct substring or word overlap
            if any(w in tag for w in signal_words if len(w) > 3) or signal in tag or tag in signal:
                matches += 1
                break

    # Calculate base affinity from match ratio
    match_ratio = min(matches / max(total_checks, 1), 1.0)
    base_score = 0.50 + (match_ratio * 0.40) # range 0.50 -> 0.90

    # Add a pseudo-random subtle jitter based on candidate name + signals
    hash_seed = candidate_name + "".join(sorted(normalized_signals))
    jitter = (int(hashlib.md5(hash_seed.encode()).hexdigest(), 16) % 10) / 100.0 # 0.00 to 0.09
    
    score = base_score + jitter
    # Keep score neatly between 0.40 and 0.98
    clamped_score = max(0.40, min(0.98, score))
    return round(clamped_score, 2)

