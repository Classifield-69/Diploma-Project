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

    try {
        const data = await fetchMovies();
        gridElement.innerHTML = data.movies.map(renderMovieCard).join("");
    } catch (error) {
        // Логваме грешката в конзолата за debug
        console.error("Грешка при зареждане на филмите:", error);
        // Показваме съобщение в самия grid вместо в отделен status елемент
        gridElement.innerHTML = `<p style="color: red;">Грешка при зареждане: ${error.message}</p>`;
    }
}

// Изпълняваме loadMovies() след като DOM-ът се зареди.
// DOMContentLoaded гарантира че #movies-grid вече съществува.
document.addEventListener("DOMContentLoaded", loadMovies);