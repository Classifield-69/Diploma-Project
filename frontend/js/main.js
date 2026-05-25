/**
 * Логика за главната страница (index.html).
 *
 * Какво прави:
 * 1. При зареждане на страницата – извиква API-то за филмите
 * 2. За всеки филм създава HTML карта (постер + заглавие + година)
 * 3. Добавя картите в #movies-grid контейнера
 * 4. Хваща грешки и ги показва на потребителя
 */

/**
 * Рендерира една карта за филм.
 * Картата е кликаема – води към /movies/<id>.
 *
 * @param {object} movie – филмов обект от API-то
 * @returns {string} – HTML низ за картата
 */
function renderMovieCard(movie) {
    const posterUrl = staticUrl(movie.poster_url);
    const genres = movie.genres.join(", ");

    return `
        <a href="/movies/${movie.id}" class="movie-card-link">
            <article class="movie-card" data-movie-id="${movie.id}">
                <img
                    src="${posterUrl}"
                    alt="Постер на ${movie.title}"
                    class="movie-poster"
                >
                <h3 class="movie-title">${movie.title}</h3>
                <p class="movie-year">${movie.year}</p>
                <p class="movie-director">Режисьор: ${movie.director}</p>
                <p class="movie-genres">${genres}</p>
            </article>
        </a>
    `;
}

/**
 * Зарежда филмите от API-то и ги показва на страницата.
 */
async function loadMovies() {
    const gridElement = document.getElementById("movies-grid");
    const statusElement = document.getElementById("status");

    try {
        statusElement.textContent = "Зареждане на филмите...";

        const data = await fetchMovies();

        // Генерираме HTML за всички филми и го слагаме в grid-а.
        // .map() + .join("") е стандартен pattern за рендериране на масиви.
        gridElement.innerHTML = data.movies.map(renderMovieCard).join("");

        statusElement.textContent = `Заредени ${data.count} филма.`;
    } catch (error) {
        // Ако нещо се обърка – показваме грешката, не "тиха" авария
        console.error("Грешка при зареждане на филмите:", error);
        statusElement.textContent = `Грешка: ${error.message}`;
        statusElement.style.color = "red";
    }
}


// Изпълняваме loadMovies() след като DOM-ът се зареди.
// DOMContentLoaded гарантира че #movies-grid вече съществува.
document.addEventListener("DOMContentLoaded", loadMovies);