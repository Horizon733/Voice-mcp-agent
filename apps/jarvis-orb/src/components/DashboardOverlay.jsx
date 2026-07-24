import { useEffect, useMemo, useState } from "react";
import AnalogWavesPanel from "./AnalogWavesPanel";

const WEATHER_CODE_LABELS = {
  0: "Clear sky",
  1: "Mainly clear",
  2: "Partly cloudy",
  3: "Overcast",
  45: "Fog",
  48: "Rime fog",
  51: "Light drizzle",
  53: "Moderate drizzle",
  55: "Dense drizzle",
  56: "Freezing drizzle",
  57: "Dense freezing drizzle",
  61: "Slight rain",
  63: "Moderate rain",
  65: "Heavy rain",
  66: "Freezing rain",
  67: "Heavy freezing rain",
  71: "Slight snow",
  73: "Moderate snow",
  75: "Heavy snow",
  77: "Snow grains",
  80: "Rain showers",
  81: "Rain showers",
  82: "Violent showers",
  85: "Snow showers",
  86: "Heavy snow showers",
  95: "Thunderstorm",
  96: "Thunderstorm hail",
  99: "Severe thunderstorm hail"
};

function formatNumber(value, digits = 0) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "--";
  }

  return Number(value).toFixed(digits);
}

export default function DashboardOverlay({
  health,
  status,
  statusText,
  transcript,
  reply,
  tools = [],
  error,
  wakeEnabled,
  wakeActive,
  busy,
  recording,
  onToggleWakeWord,
  onStartRecording,
  onStopRecording,
  onStopPlayback,
}) {
  const [weatherState, setWeatherState] = useState({
    status: "loading",
    data: null,
    error: ""
  });

  useEffect(() => {
    let cancelled = false;

    const setFailure = (message) => {
      if (!cancelled) {
        setWeatherState({ status: "error", data: null, error: message });
      }
    };

    if (!navigator.geolocation) {
      setFailure("Geolocation unavailable");
      return () => {
        cancelled = true;
      };
    }

    navigator.geolocation.getCurrentPosition(
      async ({ coords }) => {
        try {
          const { latitude, longitude } = coords;
          const url =
            `https://api.open-meteo.com/v1/forecast?latitude=${latitude}&longitude=${longitude}` +
            "&current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m,surface_pressure,uv_index" +
            "&timezone=auto";

          const res = await fetch(url);
          if (!res.ok) {
            throw new Error("Weather API unavailable");
          }

          const json = await res.json();
          const current = json.current || {};

          if (!cancelled) {
            setWeatherState({
              status: "ready",
              error: "",
              data: {
                temp: current.temperature_2m,
                humidity: current.relative_humidity_2m,
                weatherCode: current.weather_code,
                wind: current.wind_speed_10m,
                pressure: current.surface_pressure,
                uv: current.uv_index
              }
            });
          }
        } catch {
          setFailure("Weather fetch failed");
        }
      },
      () => {
        setFailure("Location access denied");
      },
      {
        enableHighAccuracy: false,
        timeout: 12000,
        maximumAge: 1000 * 60 * 10
      }
    );

    return () => {
      cancelled = true;
    };
  }, []);

  const weatherSummary = useMemo(() => {
    if (weatherState.status === "loading") {
      return {
        tempText: "-- C",
        metaText: "Acquiring GPS and weather...",
        humidity: "--%",
        wind: "-- km/h",
        pressure: "-- hPa",
        uv: "--"
      };
    }

    if (weatherState.status === "error") {
      return {
        tempText: "-- C",
        metaText: weatherState.error,
        humidity: "--%",
        wind: "-- km/h",
        pressure: "-- hPa",
        uv: "--"
      };
    }

    const data = weatherState.data;
    const condition = WEATHER_CODE_LABELS[data.weatherCode] || "Unknown conditions";

    return {
      tempText: `${formatNumber(data.temp, 1)} C`,
      metaText: `${condition}, ${formatNumber(data.wind)} km/h wind`,
      humidity: `${formatNumber(data.humidity)}%`,
      wind: `${formatNumber(data.wind)} km/h`,
      pressure: `${formatNumber(data.pressure)} hPa`,
      uv: formatNumber(data.uv, 1)
    };
  }, [weatherState]);

  const weatherChip = weatherState.status === "ready" ? "Live" : weatherState.status === "loading" ? "Syncing" : "Offline";
  const canWakeWord = Boolean(health?.wake_word_loaded);
  const healthState = health ? health.status?.toUpperCase() || "UNKNOWN" : "BOOTING";

  return (
    <div className="hud-root">
      <div className="hud-top-controls">
        <button
          type="button"
          className={`wake-toggle ${wakeEnabled ? "on" : ""}`}
          disabled={!canWakeWord}
          onClick={onToggleWakeWord}
        >
          {!wakeEnabled
            ? "Enable wake word"
            : wakeActive
              ? "Wake word: listening"
              : "Wake word: armed"}
        </button>
        <button type="button" className="silence-btn" onClick={onStopPlayback}>
          Silence
        </button>
      </div>

      <header className="hud-title glass-panel">
        <div className="title-main">JARVIS</div>
        <div className="title-sub">Synthetic Operations Dashboard</div>
      </header>

      <section className="hud-chat glass-panel">
        <div className="panel-header">
          <span>Conversation</span>
          <span className="panel-chip">Live</span>
        </div>
        <div className="chat-log">
          <div className="chat-line">
            <span className="chat-role">YOU</span>
            <span className="chat-text">{transcript || "-"}</span>
            <span className="chat-time">INPUT</span>
          </div>
          <div className="chat-line">
            <span className="chat-role">JARVIS</span>
            <span className="chat-text">{reply || "-"}</span>
            <span className="chat-time">OUTPUT</span>
          </div>
          {tools.map((tool, idx) => (
            <div key={`${tool.name}-${idx}`} className="chat-line">
              <span className="chat-role">TOOL</span>
              <span className="chat-text">{tool.name}: {tool.result_preview || "executed"}</span>
              <span className="chat-time">TRACE</span>
            </div>
          ))}
        </div>
        <div className="chat-input">{statusText}</div>
      </section>

      <section className="hud-weather glass-panel">
        <div className="panel-header">
          <span>Weather</span>
          <span className="panel-chip">{weatherChip}</span>
        </div>
        <div className="system-status-block">
          <div className="panel-header">
            <span>Voice Core</span>
            <span className="panel-chip">{status.toUpperCase()}</span>
          </div>
          <div className="core-readout sidebar-readout">
            <span className={health?.status === "ok" ? "ok-text" : "bad-text"}>CORE {healthState}</span>
            <span>{health?.gemini_configured ? "LLM LINKED" : "LLM OFFLINE"}</span>
            <span>{health?.jarvis_conds_loaded ? "VOICE READY" : "VOICE MISSING"}</span>
          </div>
          <div className="chat-input status-inline">{statusText}</div>
          {!canWakeWord ? <div className="core-error">Wake word unavailable on gateway</div> : null}
          {error ? <div className="core-error">{error}</div> : null}
        </div>
        <div className="weather-main">
          <div className="weather-temp">{weatherSummary.tempText}</div>
          <div className="weather-meta">{weatherSummary.metaText}</div>
        </div>
        <div className="weather-grid">
          <div className="weather-cell">
            <span>Humidity</span>
            <strong>{weatherSummary.humidity}</strong>
          </div>
          <div className="weather-cell">
            <span>Wind</span>
            <strong>{weatherSummary.wind}</strong>
          </div>
          <div className="weather-cell">
            <span>Pressure</span>
            <strong>{weatherSummary.pressure}</strong>
          </div>
          <div className="weather-cell">
            <span>UV</span>
            <strong>{weatherSummary.uv}</strong>
          </div>
        </div>
      </section>

      <section className="hud-waves glass-panel">
        <div className="panel-header">
          <span>Analog Diagnostics</span>
          <span className="panel-chip">Signal</span>
        </div>
        <AnalogWavesPanel />
      </section>

      <div className="hud-bottom-talk">
        <button
          type="button"
          className={`hold-btn ${recording ? "live" : ""} ${busy ? "busy" : ""}`}
          disabled={busy}
          onMouseDown={onStartRecording}
          onMouseUp={onStopRecording}
          onMouseLeave={() => {
            if (recording) onStopRecording();
          }}
          onTouchStart={(e) => {
            e.preventDefault();
            onStartRecording();
          }}
          onTouchEnd={(e) => {
            e.preventDefault();
            onStopRecording();
          }}
        >
          {recording ? "Release to send" : "Hold to talk"}
        </button>
      </div>
    </div>
  );
}
