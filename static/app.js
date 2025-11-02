// app.js — Final version with player name, difficulty, and live sidebar logs

let board = [];
let selectedFrom = null;
let validMoves = [];
let gameStarted = false;
let difficulty = "medium";
let playerName = "";

document.addEventListener("DOMContentLoaded", () => {
  const boardEl = document.getElementById("board");

  // Build board bottom → top
  for (let r = 0; r < 8; r++) {
    for (let f = 0; f < 8; f++) {
      const sq = document.createElement("div");
      sq.className = "square " + ((r + f) % 2 === 0 ? "light" : "dark");
      sq.dataset.index = f + 8 * r;
      sq.addEventListener("click", onSquareClick);
      boardEl.appendChild(sq);
      board.push(sq);
    }
  }

  document.getElementById("startBtn").addEventListener("click", startGame);
  document.getElementById("difficulty").addEventListener("change", (e) => {
    difficulty = e.target.value;
  });

  drawBoard();
  loadLogs();                   // load once on startup
  setInterval(loadLogs, 30000); // auto-refresh logs every 30 seconds
});

async function startGame() {
  const nameInput = document.getElementById("playerName");
  playerName = nameInput.value.trim();

  if (!playerName) {
    alert("Please enter your name before starting the game.");
    nameInput.focus();
    return;
  }

  const res = await fetch("/start", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ player: playerName }),
  });

  const data = await res.json();
  gameStarted = true;
  console.log("Game started for:", data.player);
  drawBoard();
}

async function drawBoard() {
  const res = await fetch("/get_state");
  const data = await res.json();
  const fen = (data.fen || "").split(" ")[0];
  if (!fen) return console.error("Invalid FEN:", data);

  board.forEach((sq) => (sq.textContent = ""));
  const ranks = fen.split("/");

  for (let r = 0; r < 8; r++) {
    const row = ranks[7 - r];
    let f = 0;
    for (const c of row) {
      if (isNaN(c)) {
        const idx = f + 8 * r;
        board[idx].textContent = pieceUnicode(c);
        f++;
      } else {
        f += parseInt(c, 10);
      }
    }
  }
}

function pieceUnicode(p) {
  const map = {
    r: "♜", n: "♞", b: "♝", q: "♛", k: "♚", p: "♟",
    R: "♖", N: "♘", B: "♗", Q: "♕", K: "♔", P: "♙",
  };
  return map[p] || "";
}

function onSquareClick(e) {
  if (!gameStarted) return;
  const index = parseInt(e.target.dataset.index);
  if (selectedFrom === null) {
    selectedFrom = index;
    showValidMoves(index);
  } else if (validMoves.includes(index)) {
    makeMove(selectedFrom, index);
    selectedFrom = null;
    validMoves = [];
    clearDots();
  } else {
    selectedFrom = null;
    validMoves = [];
    clearDots();
  }
}

function idxToAlg(i) {
  const file = String.fromCharCode(97 + (i % 8));
  const rank = Math.floor(i / 8) + 1;
  return file + rank;
}

function algToIdx(alg) {
  const file = alg.charCodeAt(0) - 97;
  const rank = parseInt(alg[1], 10) - 1;
  return file + 8 * rank;
}

async function showValidMoves(fromIndex) {
  const fromAlg = idxToAlg(fromIndex);
  const res = await fetch(`/valid_moves/${fromAlg}`);
  const data = await res.json();
  validMoves = (data.moves || []).map((m) => algToIdx(m.slice(2, 4)));
  drawDots(validMoves);
}

function drawDots(indices) {
  clearDots();
  for (const i of indices) {
    const dot = document.createElement("div");
    dot.className = "dot";
    board[i].appendChild(dot);
  }
}

function clearDots() {
  document.querySelectorAll(".dot").forEach((d) => d.remove());
}

async function makeMove(from, to) {
  const fromAlg = idxToAlg(from);
  const toAlg = idxToAlg(to);

  const res = await fetch("/player_move", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      move: fromAlg + toAlg,
      difficulty,
      player: playerName,
    }),
  });

  const data = await res.json();
  drawBoard();

  if (data.status === "finished") {
    alert("Game Over!\n" + data.result);
    loadLogs(); // refresh sidebar log immediately after each game
  }
}

// Sidebar log loader
async function loadLogs() {
  const logEl = document.getElementById("logContent");
  try {
    const res = await fetch("/logs");
    const text = await res.text();
    logEl.textContent = text || "No games yet.";
    logEl.scrollTop = logEl.scrollHeight; // auto-scroll to bottom
  } catch (err) {
    logEl.textContent = "Error loading logs.";
  }
}
