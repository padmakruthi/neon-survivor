# Neon Survivor

A fast-paced, retro-style "Survivor" game featuring neon wireframe visuals and a dynamic 3D background. Move your ship to avoid relentless enemies, automatically shoot them down, and survive as long as possible!

## Technologies Used

### Frontend
- **HTML5 Canvas (2D API):** Used for rendering the core gameplay loop, including the player ship, enemies, projectiles, and particle explosions.
- **Three.js (WebGL):** Used to create the immersive, moving 3D grid background that gives the game its retro-futuristic depth.
- **Vanilla JavaScript:** Handles all game logic, physics (using vector math), collision detection, enemy spawning, and mobile touch support.

### Backend
- **Python & Flask:** A lightweight backend server that serves the game interface and provides a REST API (`/api/scores`) to manage the leaderboard.
- **SQLite:** A serverless relational database used to persistently store player scores and names for the global leaderboard.

### Deployment & Hosting
- **Vercel:** The game is configured (via `vercel.json`) to be deployed and hosted seamlessly as a serverless Flask application on Vercel.

---

## Technical Implementation Details

The project relies on a few key technical concepts to run smoothly and look visually stunning in the browser:

### 1. Layered Graphics (2D over 3D)
To achieve the neon retro aesthetic, the game utilizes two separate `<canvas>` elements overlapping via CSS `z-index`:
- The background canvas (`#bgCanvas`) runs a **Three.js** scene with a moving, perspective WebGL grid to simulate forward momentum.
- The foreground canvas (`#gameCanvas`) uses the **2D Canvas API**. Instead of painting a solid background every frame, it uses `ctx.clearRect()` to remain transparent, allowing the 3D WebGL background to show through perfectly.

### 2. Custom Physics & Vector Math
Rather than relying on an external physics engine, the game implements its own `Vector` class from scratch. 
- All entities (Player, Enemies, Bullets) track their position and velocity using vectors.
- Calculations like `normalize()`, `mag()`, and `dist()` are used constantly. For example, enemies calculate the direction vector towards the player and normalize it to chase them.

### 3. Object-Oriented Game Entities
The architecture uses ES6 JavaScript Classes for entity management:
- Classes like `Player`, `Enemy`, `Bullet`, and `Particle` encapsulate their own state (speed, size, life) and logic (`update()` and `draw()` methods).
- The main game loop simply iterates over arrays of these objects, updating their positions based on delta time (`dt`) and drawing them to the screen.

### 4. Collision Detection
The game relies on simple, highly-performant circle-based collision detection. 
- By calculating the Euclidean distance between two entities using their position vectors (`pos.dist(other.pos)`), the game determines if they intersect by checking if the distance is less than the sum of their radii (`size`).

### 5. Cross-Platform Input Handling
The game intercepts both Mouse and Touch inputs dynamically:
- Standard `mousemove` events translate desktop interactions.
- `touchstart` and `touchmove` handle mobile devices, calculating touches and bypassing the browser's default scrolling/refreshing behavior by applying CSS `touch-action: none`.

### 6. Asynchronous Backend API
The frontend interacts with the Python/Flask backend without refreshing the page. 
- When a game ends, the browser uses the native `fetch()` API to send a `POST` request with a JSON payload to `/api/scores`.
- It then queries the database via a `GET` request to dynamically re-render the global leaderboard.

---

## Features
- **Cross-Platform Play:** Playable on both desktop (mouse to aim/move) and mobile devices (touch/drag to move).
- **Infinite Gameplay:** Enemies spawn at an increasing rate, challenging you to survive as time goes on.
- **Global Leaderboard:** Compete with other players and submit your high score when it's game over.
- **Data Export:** Download the leaderboard as a CSV file directly from the UI.

## How to Run Locally

1. **Prerequisites:** Ensure you have Python installed on your machine.
2. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
3. **Start the Server:**
   ```bash
   python app.py
   ```
4. **Play:** Open your web browser and navigate to `http://127.0.0.1:5000` to start playing!
