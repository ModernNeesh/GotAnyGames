const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

function App() {
  return (
    <div>
      <h1>GotAnyGames</h1>
      <p>Video game recommendations for groups of friends.</p>
      <p>API: {API_URL}</p>
    </div>
  )
}

export default App
