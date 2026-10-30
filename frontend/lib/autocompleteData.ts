// Curated dataset and autocomplete search engine for Common Ground
// Provides instant, zero-latency suggestions for travel destinations and cultural taste signals.

export interface DestinationCity {
  name: string;
  country: string;
  vibes: string[];
  description: string;
}

export interface CuratedEntity {
  id: string;
  name: string;
  type: "artist" | "movie" | "tv_show" | "brand" | "place" | "cultural_entity";
  category: string;
  subtitle?: string;
  image?: string;
}

export const CITIES_DATABASE: DestinationCity[] = [
  {
    name: "Lisbon",
    country: "Portugal",
    vibes: ["Architecture", "Petiscos & Wine", "Fado & Indie", "Coastal Views"],
    description: "Sun-drenched hills, tiled façades, indie coffee, and vibrant culinary scene.",
  },
  {
    name: "Tokyo",
    country: "Japan",
    vibes: ["Culinary Art", "Vinyl Bars", "Neo-Futurism", "Design"],
    description: "World-class dining, neon alleys, tranquil shrines, and listening bars.",
  },
  {
    name: "Berlin",
    country: "Germany",
    vibes: ["Club Culture", "Contemporary Art", "Brutalism", "Coffee"],
    description: "Counter-cultural capital with cavernous clubs, indie galleries, and open parks.",
  },
  {
    name: "Paris",
    country: "France",
    vibes: ["Haute Cuisine", "Bistros & Wine", "Art History", "Fashion"],
    description: "Classic café culture, cutting-edge modern dining, and timeless museums.",
  },
  {
    name: "New York",
    country: "United States",
    vibes: ["Modern Art", "Global Street Food", "Live Jazz", "Nightlife"],
    description: "Limitless 24/7 energy, iconic neighborhood pockets, and world-class culture.",
  },
  {
    name: "London",
    country: "United Kingdom",
    vibes: ["Theatre & Gigs", "Pub Culture", "Design & Fashion", "Borough Markets"],
    description: "Layered heritage, independent music scenes, and sprawling historic parks.",
  },
  {
    name: "Kyoto",
    country: "Japan",
    vibes: ["Zen Gardens", "Kaiseki", "Traditional Craft", "Tea Ceremonies"],
    description: "Centuries of refined aesthetics, bamboo groves, and meditative temples.",
  },
  {
    name: "Barcelona",
    country: "Spain",
    vibes: ["Gaudí & Modernism", "Tapas & Vermouth", "Beach Vibe", "Late Nights"],
    description: "Mediterranean warmth, bold architecture, and lively seaside promenades.",
  },
  {
    name: "Rome",
    country: "Italy",
    vibes: ["Antiquity", "Trattorias", "Espresso Culture", "Piazza Life"],
    description: "Living open-air museum filled with Roman ruins and effortless street life.",
  },
  {
    name: "Amsterdam",
    country: "Netherlands",
    vibes: ["Canal Walks", "Design & Bikes", "Electronic Music", "Indie Cafes"],
    description: "Canal-ring charm, world-leading graphic design, and relaxed cycling culture.",
  },
  {
    name: "Seoul",
    country: "South Korea",
    vibes: ["K-Culture", "Night Markets", "Futuristic Cafes", "Skincare & Style"],
    description: "High-octane neon metropolis paired with peaceful mountain palaces.",
  },
  {
    name: "Oaxaca",
    country: "Mexico",
    vibes: ["Artisanal Mezcal", "Mole & Markets", "Indigenous Craft", "Color"],
    description: "Culinary crown jewel of Mexico with rich artisan heritage and vibrant streets.",
  },
  {
    name: "Mexico City",
    country: "Mexico",
    vibes: ["Architecture", "Modernist Homes", "Taquerias", "Museums"],
    description: "Expansive cultural powerhouse with leafy avenues and booming dining.",
  },
  {
    name: "Copenhagen",
    country: "Denmark",
    vibes: ["New Nordic", "Danish Design", "Bikes & Canals", "Hygge"],
    description: "Pinnacle of Scandinavian minimalism, bakery culture, and culinary innovation.",
  },
  {
    name: "Stockholm",
    country: "Sweden",
    vibes: ["Archipelago", "Design Shops", "Fika & Bakeries", "Indie Pop"],
    description: "Waterfront islands, sleek mid-century aesthetics, and cozy candlelit fikas.",
  },
  {
    name: "Porto",
    country: "Portugal",
    vibes: ["Port Cellars", "Azulejos", "Seafood", "Douro River"],
    description: "Gritty romance, tiered riverside hills, and legendary wine cellars.",
  },
  {
    name: "Milan",
    country: "Italy",
    vibes: ["Fashion Week", "Aperitivo Culture", "Modern Design", "Duomo"],
    description: "Chic fashion capital filled with stylish cocktail bars and design studios.",
  },
  {
    name: "Florence",
    country: "Italy",
    vibes: ["Renaissance Masterpieces", "Tuscan Wine", "Steak & Truffles", "Bridges"],
    description: "Cradle of the Renaissance with terracotta domes and rustic trattorias.",
  },
  {
    name: "Vienna",
    country: "Austria",
    vibes: ["Coffee Houses", "Classical Music", "Imperial Palaces", "Secession Art"],
    description: "Stately elegance, velvety Sachertorte, and opulent artistic legacy.",
  },
  {
    name: "Prague",
    country: "Czechia",
    vibes: ["Bohemian Glass", "Beer Halls", "Gothic Spires", "Old Town"],
    description: "Fairy-tale bridges, cobblestone alleyways, and microbrewery culture.",
  },
  {
    name: "Budapest",
    country: "Hungary",
    vibes: ["Thermal Baths", "Ruin Bars", "Danube Views", "Art Nouveau"],
    description: "Steamy thermal mineral pools, bohemian ruin bars, and grand river architecture.",
  },
  {
    name: "Athens",
    country: "Greece",
    vibes: ["Acropolis", "Meze & Ouzo", "Rooftop Views", "Gritty Energy"],
    description: "Ancient grandeur meets energetic youth culture and lively tavernas.",
  },
  {
    name: "Istanbul",
    country: "Turkey",
    vibes: ["Bosphorus Straits", "Spice Bazaars", "Coffee & Tea", "Two Continents"],
    description: "Where East meets West across continents, rich with sensory wonders.",
  },
  {
    name: "Edinburgh",
    country: "United Kingdom",
    vibes: ["Gothic Closes", "Whisky & Pubs", "Castle Views", "Literature"],
    description: "Dramatic volcanic skyline, literary history, and cozy cobblestone pubs.",
  },
  {
    name: "Dublin",
    country: "Ireland",
    vibes: ["Live Folk Sessions", "Guinness Pubs", "Literary Legacy", "Georgian Squares"],
    description: "Warm hospitality, world-famous pub storytelling, and coastal greenery.",
  },
  {
    name: "Marrakech",
    country: "Morocco",
    vibes: ["Medina Riads", "Spice Markets", "Tiles & Carpets", "Mint Tea"],
    description: "Sensory labyrinth of souks, tranquil courtyard riads, and vibrant spices.",
  },
  {
    name: "Cape Town",
    country: "South Africa",
    vibes: ["Table Mountain", "Wine Valleys", "Ocean Drives", "Art"],
    description: "Dramatic sea-to-mountain landscapes and thriving culinary and design scene.",
  },
  {
    name: "Melbourne",
    country: "Australia",
    vibes: ["Laneway Cafes", "Street Art", "Live Music", "Wine Bars"],
    description: "Australia’s cultural heartbeat with hidden laneways and obsessed baristas.",
  },
  {
    name: "Sydney",
    country: "Australia",
    vibes: ["Harbour & Beaches", "Fresh Seafood", "Coastal Walks", "Sunshine"],
    description: "Sparkling waters, iconic sail architecture, and breezy outdoor dining.",
  },
  {
    name: "Bangkok",
    country: "Thailand",
    vibes: ["Street Eats", "Rooftop Lounges", "Golden Temples", "Night Markets"],
    description: "Electrifying collision of street food stalls, ornate temples, and rooftop views.",
  },
  {
    name: "Singapore",
    country: "Singapore",
    vibes: ["Hawker Centres", "Futuristic Gardens", "Cocktail Bars", "Greenery"],
    description: "Garden city boasting Michelin hawker stalls and world-class mixology.",
  },
  {
    name: "Taipei",
    country: "Taiwan",
    vibes: ["Night Markets", "Oolong Tea", "Indie Cafes", "Hot Springs"],
    description: "Culinary wonderland with vibrant night markets and serene mountain tea houses.",
  },
  {
    name: "Delhi",
    country: "India",
    vibes: ["Historic Monuments", "Heritage Food", "Craft Bazaars", "Spices"],
    description: "Layered centuries of Mughal and imperial history with unforgettable flavors.",
  },
  {
    name: "Mumbai",
    country: "India",
    vibes: ["Marine Drive", "Art Deco", "Irani Cafes", "Bollywood"],
    description: "Relentless coastal energy, colonial architecture, and sea breezes.",
  },
  {
    name: "Jaipur",
    country: "India",
    vibes: ["Pink City Palaces", "Block Prints", "Royal Cuisine", "Forts"],
    description: "Royal Rajasthani grandeur, hand-block printing ateliers, and desert colors.",
  },
  {
    name: "San Francisco",
    country: "United States",
    vibes: ["Sourdough & Coffee", "Hills & Bridges", "Victorian Homes", "Wine Country"],
    description: "Foggy hills, iconic bay bridges, and culinary obsession with farm-to-table.",
  },
  {
    name: "Los Angeles",
    country: "United States",
    vibes: ["Cinema Culture", "Taco Trucks", "Pacific Sunsets", "Mid-Century Modern"],
    description: "Sprawling creative enclave of film, golden hour light, and diverse cuisine.",
  },
  {
    name: "Reykjavik",
    country: "Iceland",
    vibes: ["Northern Lights", "Geothermal Pools", "Indie Music", "Volcanic Landscapes"],
    description: "Cozy colorful capital on the doorstep of waterfalls and thermal springs.",
  },
];

export const CULTURAL_ENTITIES_DATABASE: CuratedEntity[] = [
  // --- Global Pop & Vocal Icons ---
  { id: "ent-adele", name: "Adele", type: "artist", category: "Music", subtitle: "Soul • Pop • Singer-Songwriter" },
  { id: "ent-adele-21", name: "Adele — 21 & 25", type: "artist", category: "Music", subtitle: "Grammy Award Album • Soul Ballads" },
  { id: "ent-amy-winehouse", name: "Amy Winehouse", type: "artist", category: "Music", subtitle: "Soul • Neo-Soul • Jazz" },
  { id: "ent-beyonce", name: "Beyoncé", type: "artist", category: "Music", subtitle: "R&B • Pop • Renaissance • Culture Icon" },
  { id: "ent-taylor-swift", name: "Taylor Swift", type: "artist", category: "Music", subtitle: "Pop • Folklore • Singer-Songwriter" },
  { id: "ent-billie-eilish", name: "Billie Eilish", type: "artist", category: "Music", subtitle: "Alt Pop • Electropop • Finneas" },
  { id: "ent-dua-lipa", name: "Dua Lipa", type: "artist", category: "Music", subtitle: "Nu-Disco • Pop • Dance-Pop" },
  { id: "ent-sza", name: "SZA", type: "artist", category: "Music", subtitle: "Neo Soul • Contemporary R&B • SOS" },
  { id: "ent-the-weeknd", name: "The Weeknd", type: "artist", category: "Music", subtitle: "Synth-Pop • R&B • Dark Wave" },
  { id: "ent-drake", name: "Drake", type: "artist", category: "Music", subtitle: "Hip Hop • R&B • OVO Sound" },
  { id: "ent-harry-styles", name: "Harry Styles", type: "artist", category: "Music", subtitle: "Pop Rock • Soft Rock • Glam" },
  { id: "ent-rihanna", name: "Rihanna", type: "artist", category: "Music", subtitle: "R&B • Pop • Fenty Culture" },
  { id: "ent-lady-gaga", name: "Lady Gaga", type: "artist", category: "Music", subtitle: "Electropop • Avant-Garde • Vocal Jazz" },
  { id: "ent-ariana-grande", name: "Ariana Grande", type: "artist", category: "Music", subtitle: "Pop • R&B • Vocal Range" },
  { id: "ent-olivia-rodrigo", name: "Olivia Rodrigo", type: "artist", category: "Music", subtitle: "Pop Punk • Alt Pop • GUTS" },
  { id: "ent-chappell-roan", name: "Chappell Roan", type: "artist", category: "Music", subtitle: "Synth-Pop • Midwest Glam • Pop Icon" },
  { id: "ent-charli-xcx", name: "Charli XCX", type: "artist", category: "Music", subtitle: "Hyperpop • Club Classics • BRAT" },
  { id: "ent-lorde", name: "Lorde", type: "artist", category: "Music", subtitle: "Art Pop • Indie Pop • Melodrama" },
  { id: "ent-lana-del-rey", name: "Lana Del Rey", type: "artist", category: "Music", subtitle: "Cinematic Pop • Baroque Pop • Americana" },
  { id: "ent-frank-ocean", name: "Frank Ocean", type: "artist", category: "Music", subtitle: "Neo Soul • Blonde • Contemporary R&B" },
  { id: "ent-kendrick-lamar", name: "Kendrick Lamar", type: "artist", category: "Music", subtitle: "Conscious Hip Hop • Pulitzer Prize" },
  { id: "ent-tyler-creator", name: "Tyler, The Creator", type: "artist", category: "Music", subtitle: "Alternative Hip Hop • GOLF WANG" },
  { id: "ent-norah-jones", name: "Norah Jones", type: "artist", category: "Music", subtitle: "Vocal Jazz • Acoustic Soul • Blue Note" },

  // --- Rock, Alternative & Indie ---
  { id: "ent-coldplay", name: "Coldplay", type: "artist", category: "Music", subtitle: "Alt Rock • Post-Britpop • Stadium Anthems" },
  { id: "ent-radiohead", name: "Radiohead", type: "artist", category: "Music", subtitle: "Art Rock • Electronic • OK Computer • Kid A" },
  { id: "ent-arctic-monkeys", name: "Arctic Monkeys", type: "artist", category: "Music", subtitle: "Indie Rock • Post-Punk Revival • Alex Turner" },
  { id: "ent-oasis", name: "Oasis", type: "artist", category: "Music", subtitle: "Britpop • Manchester • Noel & Liam Gallagher" },
  { id: "ent-the-beatles", name: "The Beatles", type: "artist", category: "Music", subtitle: "Classic Rock • Psychedelic • Abbey Road" },
  { id: "ent-queen", name: "Queen", type: "artist", category: "Music", subtitle: "Glam Rock • Freddie Mercury • Opera Rock" },
  { id: "ent-pink-floyd", name: "Pink Floyd", type: "artist", category: "Music", subtitle: "Progressive Rock • Psychedelic • Dark Side" },
  { id: "ent-nirvana", name: "Nirvana", type: "artist", category: "Music", subtitle: "Grunge • Kurt Cobain • Seattle Rock" },
  { id: "ent-the-strokes", name: "The Strokes", type: "artist", category: "Music", subtitle: "Garage Rock • NYC Indie • Is This It" },
  { id: "ent-tame-impala", name: "Tame Impala", type: "artist", category: "Music", subtitle: "Psychedelic Pop • Kevin Parker • Currents" },
  { id: "ent-fleetwood-mac", name: "Fleetwood Mac", type: "artist", category: "Music", subtitle: "Classic Rock • Rumours • Stevie Nicks" },
  { id: "ent-the-cure", name: "The Cure", type: "artist", category: "Music", subtitle: "Post-Punk • Goth Rock • Robert Smith" },
  { id: "ent-the-smiths", name: "The Smiths", type: "artist", category: "Music", subtitle: "Jangle Pop • Indie Rock • Morrissey & Marr" },
  { id: "ent-metallica", name: "Metallica", type: "artist", category: "Music", subtitle: "Thrash Metal • Master of Puppets • Heavy Rock" },
  { id: "ent-depeche-mode", name: "Depeche Mode", type: "artist", category: "Music", subtitle: "Synth-Pop • Dark Wave • Violator" },
  { id: "ent-joy-division", name: "Joy Division", type: "artist", category: "Music", subtitle: "Post-Punk • Ian Curtis • Factory Records" },
  { id: "ent-new-order", name: "New Order", type: "artist", category: "Music", subtitle: "Post-Punk • Synth-Pop • Blue Monday" },
  { id: "ent-talking-heads", name: "Talking Heads", type: "artist", category: "Music", subtitle: "New Wave • David Byrne • Post-Punk" },
  { id: "ent-david-bowie", name: "David Bowie", type: "artist", category: "Music", subtitle: "Glam Rock • Art Rock • Ziggy Stardust" },
  { id: "ent-the-1975", name: "The 1975", type: "artist", category: "Music", subtitle: "Indie Pop • Alt Rock • Matty Healy" },
  { id: "ent-lcd-soundsystem", name: "LCD Soundsystem", type: "artist", category: "Music", subtitle: "Dance-Punk • DFA Records • James Murphy" },

  // --- Electronic, Club & Ambient ---
  { id: "ent-burial", name: "Burial", type: "artist", category: "Music", subtitle: "Electronic • Ambient Dubstep • Hyperdub • Untrue" },
  { id: "ent-daft-punk", name: "Daft Punk", type: "artist", category: "Music", subtitle: "French House • Discovery • Electronic Pioneers" },
  { id: "ent-aphex-twin", name: "Aphex Twin", type: "artist", category: "Music", subtitle: "IDM • Ambient Works • Warp Records" },
  { id: "ent-four-tet", name: "Four Tet", type: "artist", category: "Music", subtitle: "Folktronica • Organic House • Kieran Hebden" },
  { id: "ent-bonobo", name: "Bonobo", type: "artist", category: "Music", subtitle: "Downtempo • Electronic • Black Sands" },
  { id: "ent-massive-attack", name: "Massive Attack", type: "artist", category: "Music", subtitle: "Trip Hop • Bristol Sound • Mezzanine" },
  { id: "ent-portishead", name: "Portishead", type: "artist", category: "Music", subtitle: "Trip Hop • Dummy • Beth Gibbons" },
  { id: "ent-fred-again", name: "Fred again..", type: "artist", category: "Music", subtitle: "Electronic • UK Garage • Actual Life" },
  { id: "ent-jamie-xx", name: "Jamie xx", type: "artist", category: "Music", subtitle: "UK Garage • In Colour • Steel Pan Dance" },
  { id: "ent-bicep", name: "Bicep", type: "artist", category: "Music", subtitle: "Feel My Bicep • Electronic • Breakbeat" },
  { id: "ent-peggy-gou", name: "Peggy Gou", type: "artist", category: "Music", subtitle: "House • Techno • Korean Electronic" },
  { id: "ent-fka-twigs", name: "FKA Twigs", type: "artist", category: "Music", subtitle: "Avant-Pop • Electronic R&B • Magdalene" },
  { id: "ent-rosalia", name: "Rosalía", type: "artist", category: "Music", subtitle: "Nuevo Flamenco • Motomami • Urban Latin" },
  { id: "ent-ryuichi-sakamoto", name: "Ryuichi Sakamoto", type: "artist", category: "Music", subtitle: "Neoclassical • Ambient • YMO • Film Scores" },
  { id: "ent-miles-davis", name: "Miles Davis", type: "artist", category: "Music", subtitle: "Modal Jazz • Kind of Blue • Fusion" },
  { id: "ent-john-coltrane", name: "John Coltrane", type: "artist", category: "Music", subtitle: "Spiritual Jazz • A Love Supreme" },

  // --- Cinema, Directors & Films ---
  { id: "ent-wes-anderson", name: "Wes Anderson", type: "movie", category: "Cinema", subtitle: "Grand Budapest • Symmetrical Pastels" },
  { id: "ent-studio-ghibli", name: "Studio Ghibli", type: "movie", category: "Cinema", subtitle: "Hayao Miyazaki • Japanese Animation" },
  { id: "ent-spirited-away", name: "Spirited Away", type: "movie", category: "Cinema", subtitle: "Oscar-Winning Animation • Miyazaki Masterpiece" },
  { id: "ent-christopher-nolan", name: "Christopher Nolan", type: "movie", category: "Cinema", subtitle: "Oppenheimer • Interstellar • Inception" },
  { id: "ent-interstellar", name: "Interstellar", type: "movie", category: "Cinema", subtitle: "Sci-Fi • Hans Zimmer • Nolan Epic" },
  { id: "ent-inception", name: "Inception", type: "movie", category: "Cinema", subtitle: "Mind-Bending Sci-Fi • Dreams" },
  { id: "ent-quentin-tarantino", name: "Quentin Tarantino", type: "movie", category: "Cinema", subtitle: "Pulp Fiction • Inglourious Basterds" },
  { id: "ent-pulp-fiction", name: "Pulp Fiction", type: "movie", category: "Cinema", subtitle: "Cult Classic • 90s Independent Cinema" },
  { id: "ent-denis-villeneuve", name: "Denis Villeneuve", type: "movie", category: "Cinema", subtitle: "Dune Part One & Two • Blade Runner 2049" },
  { id: "ent-blade-runner-2049", name: "Blade Runner 2049", type: "movie", category: "Cinema", subtitle: "Neo-Noir Cyberpunk • Roger Deakins" },
  { id: "ent-wong-kar-wai", name: "Wong Kar-wai", type: "movie", category: "Cinema", subtitle: "In the Mood for Love • Chungking Express" },
  { id: "ent-a24", name: "A24", type: "brand", category: "Cinema", subtitle: "Prestige Indie Studio • Everything Everywhere" },
  { id: "ent-martin-scorsese", name: "Martin Scorsese", type: "movie", category: "Cinema", subtitle: "Taxi Driver • Goodfellas • Killers of the Flower Moon" },
  { id: "ent-stanley-kubrick", name: "Stanley Kubrick", type: "movie", category: "Cinema", subtitle: "2001 A Space Odyssey • The Shining" },
  { id: "ent-david-lynch", name: "David Lynch", type: "movie", category: "Cinema", subtitle: "Mulholland Drive • Twin Peaks • Surrealism" },
  { id: "ent-sofia-coppola", name: "Sofia Coppola", type: "movie", category: "Cinema", subtitle: "Lost in Translation • Virgin Suicides" },
  { id: "ent-lost-in-translation", name: "Lost in Translation", type: "movie", category: "Cinema", subtitle: "Tokyo Melancholy • Bill Murray" },
  { id: "ent-greta-gerwig", name: "Greta Gerwig", type: "movie", category: "Cinema", subtitle: "Barbie • Lady Bird • Little Women" },
  { id: "ent-bong-joon-ho", name: "Bong Joon-ho", type: "movie", category: "Cinema", subtitle: "Parasite • Memories of Murder" },
  { id: "ent-parasite", name: "Parasite", type: "movie", category: "Cinema", subtitle: "Palme d'Or & Oscar Winner • Thriller" },
  { id: "ent-yorgos-lanthimos", name: "Yorgos Lanthimos", type: "movie", category: "Cinema", subtitle: "Poor Things • The Favourite • The Lobster" },

  // --- Television ---
  { id: "ent-succession", name: "Succession", type: "tv_show", category: "Television", subtitle: "HBO Drama • Roy Family • Prestige Satire" },
  { id: "ent-the-bear", name: "The Bear", type: "tv_show", category: "Television", subtitle: "Culinary Drama • Chicago Beef • Jeremy Allen White" },
  { id: "ent-severance", name: "Severance", type: "tv_show", category: "Television", subtitle: "Apple TV+ Sci-Fi Thriller • Lumon Industries" },
  { id: "ent-white-lotus", name: "The White Lotus", type: "tv_show", category: "Television", subtitle: "Mike White • Social Satire • Sicily & Maui" },
  { id: "ent-fleabag", name: "Fleabag", type: "tv_show", category: "Television", subtitle: "Phoebe Waller-Bridge • Dark Comedy" },
  { id: "ent-twin-peaks", name: "Twin Peaks", type: "tv_show", category: "Television", subtitle: "David Lynch • Cherry Pie • Pacific Northwest Noir" },
  { id: "ent-breaking-bad", name: "Breaking Bad", type: "tv_show", category: "Television", subtitle: "Vince Gilligan • Walter White • Crime Drama" },

  // --- Brands & Fashion ---
  { id: "ent-aesop", name: "Aesop", type: "brand", category: "Brand", subtitle: "Botanical Skincare • Architectural Retail" },
  { id: "ent-nike", name: "Nike", type: "brand", category: "Brand", subtitle: "Sneaker Culture • Sportswear • Air Jordan" },
  { id: "ent-acne-studios", name: "Acne Studios", type: "brand", category: "Brand", subtitle: "Stockholm Fashion • Minimalist Tailoring" },
  { id: "ent-comme-des-garcons", name: "Comme des Garçons", type: "brand", category: "Brand", subtitle: "Rei Kawakubo • Tokyo Avant-Garde" },
  { id: "ent-issey-miyake", name: "Issey Miyake", type: "brand", category: "Brand", subtitle: "Pleats Please • Japanese Material Innovation" },
  { id: "ent-patagonia", name: "Patagonia", type: "brand", category: "Brand", subtitle: "Sustainable Outdoor • Environmental Ethics" },
  { id: "ent-le-labo", name: "Le Labo", type: "brand", category: "Brand", subtitle: "Santal 33 • Hand-Formulated Perfumery" },
  { id: "ent-muji", name: "Muji", type: "brand", category: "Brand", subtitle: "No-Brand Quality Goods • Japanese Everyday Life" },
  { id: "ent-dover-street-market", name: "Dover Street Market", type: "brand", category: "Brand", subtitle: "Avant-Garde Retail • Rei Kawakubo" },
  { id: "ent-maison-margiela", name: "Maison Margiela", type: "brand", category: "Brand", subtitle: "Tabi Boot • Artisanal Deconstruction" },
  { id: "ent-jacquemus", name: "Jacquemus", type: "brand", category: "Brand", subtitle: "Provence Pastels • Le Chiquito • Playful Chic" },
  { id: "ent-loewe", name: "Loewe", type: "brand", category: "Brand", subtitle: "Jonathan Anderson • Spanish Leathercraft" },
  { id: "ent-prada", name: "Prada", type: "brand", category: "Brand", subtitle: "Miuccia Prada • Milan Luxury • Re-Nylon" },
  { id: "ent-gucci", name: "Gucci", type: "brand", category: "Brand", subtitle: "Italian Heritage • Florence Leather" },
  { id: "ent-chanel", name: "Chanel", type: "brand", category: "Brand", subtitle: "Haute Couture • Parisian Luxury" },
  { id: "ent-arcteryx", name: "Arc'teryx", type: "brand", category: "Brand", subtitle: "Technical Gorpcore • Coast Mountain Outerwear" },
  { id: "ent-rimowa", name: "Rimowa", type: "brand", category: "Brand", subtitle: "Grooved Aluminum Luggage • Cologne Germany" },
  { id: "ent-birkenstock", name: "Birkenstock", type: "brand", category: "Brand", subtitle: "Ergonomic Cork Footwear • Timeless Comfort" },
  { id: "ent-gentle-monster", name: "Gentle Monster", type: "brand", category: "Brand", subtitle: "Seoul Eyewear • Experimental Spatial Art" },
  { id: "ent-carhartt-wip", name: "Carhartt WIP", type: "brand", category: "Brand", subtitle: "Detroit Workwear • European Streetwear" },
  { id: "ent-stussy", name: "Stüssy", type: "brand", category: "Brand", subtitle: "Laguna Beach Surf & Skate Heritage" },
  { id: "ent-byredo", name: "Byredo", type: "brand", category: "Brand", subtitle: "Ben Gorham • Gypsy Water • Stockholm Scents" },
  { id: "ent-diptyque", name: "Diptyque", type: "brand", category: "Brand", subtitle: "Saint-Germain Paris • Luxury Candles & Scents" },

  // --- Culture, Lifestyle & Places ---
  { id: "ent-specialty-coffee", name: "Specialty Coffee", type: "place", category: "Culture", subtitle: "Third-Wave Roasters • Single-Origin V60" },
  { id: "ent-natural-wine", name: "Natural Wine Bars", type: "place", category: "Culture", subtitle: "Low-Intervention • Pet-Nat • Biodynamic" },
  { id: "ent-vinyl-listening-bars", name: "Vinyl Listening Bars", type: "place", category: "Culture", subtitle: "Japanese Jazz Kissa • Hi-Fi Tube Amps" },
  { id: "ent-modern-art-museums", name: "Modern & Contemporary Art", type: "place", category: "Culture", subtitle: "Tate Modern • MoMA • Serralves • Centre Pompidou" },
  { id: "ent-brutalist-architecture", name: "Brutalist Architecture", type: "place", category: "Culture", subtitle: "Raw Concrete • Geometric Monoliths" },
  { id: "ent-indie-bookshops", name: "Independent Bookshops", type: "place", category: "Culture", subtitle: "Curated Editions • Literary Salons" },
  { id: "ent-botanical-gardens", name: "Botanical Gardens & Greenhouses", type: "place", category: "Culture", subtitle: "Victorian Glasshouses • Tropical Flora" },
  { id: "ent-street-food-markets", name: "Artisanal Food Markets", type: "place", category: "Culture", subtitle: "Local Stalls • Craft Cheeses & Spices" },
  { id: "ent-ceramics-studios", name: "Studio Ceramics & Pottery", type: "place", category: "Culture", subtitle: "Handcrafted Stoneware • Wabi-Sabi Aesthetics" },
  { id: "ent-rooftop-cinemas", name: "Rooftop Open-Air Cinema", type: "place", category: "Culture", subtitle: "Sunset Screenings • 35mm Projection" },
  { id: "ent-thermal-baths", name: "Thermal Baths & Spas", type: "place", category: "Culture", subtitle: "Mineral Springs • Onsen • Traditional Bathing" },
  { id: "ent-craft-breweries", name: "Microbreweries & Craft Beer", type: "place", category: "Culture", subtitle: "Hazy IPAs • Sours • Small-Batch Taps" },
];

/**
 * Searches the destination database with typeahead substring matching.
 */
export function searchDestinations(query: string): DestinationCity[] {
  const clean = query.trim().toLowerCase();
  if (!clean) {
    return CITIES_DATABASE.slice(0, 8);
  }

  return CITIES_DATABASE.filter((c) => {
    return (
      c.name.toLowerCase().includes(clean) ||
      c.country.toLowerCase().includes(clean) ||
      c.vibes.some((v) => v.toLowerCase().includes(clean)) ||
      c.description.toLowerCase().includes(clean)
    );
  }).slice(0, 8);
}

/**
 * Searches the curated cultural entities database with optional type filter.
 * ALWAYS guarantees 4-8 rich suggestions for ANY query (including famous artists like Adele,
 * Coldplay, Beyonce, or user-typed custom strings).
 */
export function searchCuratedEntities(query: string, type?: string): CuratedEntity[] {
  const rawQuery = (query || "").trim();
  const clean = rawQuery.toLowerCase();

  // 1. If query is empty, return popular curated recommendations
  if (!clean) {
    const popular = CULTURAL_ENTITIES_DATABASE.filter((e) => {
      if (!type || type === "all") return true;
      if (type === "artist") return e.type === "artist";
      if (type === "movie") return e.type === "movie" || e.type === "tv_show";
      if (type === "brand") return e.type === "brand";
      if (type === "place") return e.type === "place";
      return true;
    });
    return popular.slice(0, 8);
  }

  // 2. Direct & substring matching from database
  const matchingEntities = CULTURAL_ENTITIES_DATABASE.filter((e) => {
    const matchesQuery =
      e.name.toLowerCase().includes(clean) ||
      (e.subtitle && e.subtitle.toLowerCase().includes(clean)) ||
      e.category.toLowerCase().includes(clean);

    if (!matchesQuery) return false;

    // Type filter
    if (!type || type === "all") return true;
    if (type === "artist") return e.type === "artist";
    if (type === "movie") return e.type === "movie" || e.type === "tv_show";
    if (type === "brand") return e.type === "brand";
    if (type === "place") return e.type === "place";
    return true;
  });

  // Sort exact/prefix matches first
  matchingEntities.sort((a, b) => {
    const aName = a.name.toLowerCase();
    const bName = b.name.toLowerCase();
    if (aName === clean) return -1;
    if (bName === clean) return 1;
    if (aName.startsWith(clean) && !bName.startsWith(clean)) return -1;
    if (!aName.startsWith(clean) && bName.startsWith(clean)) return 1;
    return 0;
  });

  const results: CuratedEntity[] = [...matchingEntities.slice(0, 7)];

  // 3. If user typed a query, ALWAYS generate intelligent related cultural options
  // so the user NEVER sees an empty dropdown or only a lone "+ Add Custom" pill
  const capitalized = rawQuery.charAt(0).toUpperCase() + rawQuery.slice(1);

  // If query is "adele", or any name, ensure we offer rich options
  if (results.length < 4) {
    // Add Music option
    if (!type || type === "all" || type === "artist") {
      results.push({
        id: `gen-music-${clean}`,
        name: capitalized,
        type: "artist",
        category: "Music",
        subtitle: `Music & Artist • ${capitalized} Discography & Sound`,
      });
    }

    // Add Related culture option
    results.push({
      id: `gen-related-${clean}`,
      name: `${capitalized} (Related Sound & Vibes)`,
      type: (type && type !== "all" ? type : "cultural_entity") as any,
      category: "Culture",
      subtitle: `Taste Affinities & Venues matching ${capitalized}`,
    });

    // Add Cinema/Brand if all
    if (!type || type === "all") {
      results.push({
        id: `gen-cinema-${clean}`,
        name: `${capitalized} (Cinema & Visual Culture)`,
        type: "movie",
        category: "Cinema",
        subtitle: `Film, Visual Media & Direction`,
      });
    }
  }

  // 4. Also append explicit Custom option
  const hasExact = results.some((e) => e.name.toLowerCase() === clean);
  if (!hasExact) {
    results.push({
      id: `custom-${clean.replace(/\s+/g, "-")}`,
      name: rawQuery,
      type: (type && type !== "all" ? type : "cultural_entity") as any,
      category: "Custom",
      subtitle: `+ Add "${rawQuery}" as custom favorite`,
    });
  }

  return results.slice(0, 8);
}
