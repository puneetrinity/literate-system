// Fix for search function to use POST method
async function search() {
    const query = document.getElementById('searchQuery').value.trim();
    if (\!query) return;

    const resultsDiv = document.getElementById('results');
    resultsDiv.innerHTML = '<div class="loading">🔍 Searching...</div>';

    try {
        const response = await fetch(`${API_BASE}/api/v2/search/ultra-fast`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                query: query,
                num_results: 20
            })
        });
        const data = await response.json();

        if (\!data.results || data.results.length === 0) {
            resultsDiv.innerHTML = '<div class="loading">No results found. Try different keywords.</div>';
            return;
        }

        resultsDiv.innerHTML = `
            <h3>🎯 Found ${data.total_found} result(s) in ${data.response_time_ms}ms</h3>
            ${data.results.map(result => `
                <div class="result">
                    <div class="result-title">${result.title || result.filename || 'Untitled'}</div>
                    <div class="result-content">${result.content || result.text || ''}</div>
                    <div class="result-meta">
                        Score: ${result.score?.toFixed(3) || 'N/A'}  < /dev/null |  
                        ID: ${result.id || 'N/A'}
                    </div>
                </div>
            `).join('')}
        `;
    } catch (error) {
        resultsDiv.innerHTML = '<div class="error">❌ Search failed. Please try again.</div>';
        console.error('Search error:', error);
    }
}
