import { useState } from "react";
import "./index.css";
import UploadScreen from "./UploadScreen";
import SearchScreen from "./SearchScreen";

function App() {
  const [screen, setScreen] = useState("search");

  return (
    <div className="app-shell">
      <nav className="app-nav" aria-label="Primary navigation">
        <div className="nav-links">
          <button className={screen === "search" ? "nav-link is-active" : "nav-link"} onClick={() => setScreen("search")}>Search</button>
          <button className={screen === "upload" ? "nav-link is-active" : "nav-link"} onClick={() => setScreen("upload")}>Upload</button>
        </div>
      </nav>
      <main>{screen === "search" ? <SearchScreen /> : <UploadScreen />}</main>
    </div>
  );
}

export default App;
