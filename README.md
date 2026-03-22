# FlightClaw

A lightweight flight search tool that finds *cheap round-trip flights across flexible date ranges*. FlightClaw runs a headless Chromium browser (via Playwright) to search Google Flights across date combinations, sampling top outbound and return options to surface competitively priced round trips. Filter by airlines, stops, and overnight flights. Results link directly to Google Flights for booking. Currently only supports US domestic flights (prices in USD). No API keys, no accounts, no cost. All processing runs locally.

**[Try the live demo](https://zhijieq-flightclaw.hf.space)** — hosted on Hugging Face Spaces. Note that the demo runs on shared hardware and is very slow. For faster performance, install and run FlightClaw on your own machine.

## Requirements

- Python 3.10+

## Installation

```bash
git clone https://github.com/QZJGeorge/FlightClaw.git
cd FlightClaw
pip3 install -r requirements.txt
playwright install chromium
```

## Usage

```bash
WORKERS=2 uvicorn app.main:app --reload
```

Then open [http://localhost:8000](http://localhost:8000) in your browser.

`WORKERS` controls how many date searches run in parallel. Higher values use more memory and CPU.

## Disclaimer

FlightClaw is provided as-is for informational purposes only. Flight prices, times, and availability may not be accurate or up to date. This tool does not book or purchase flights on your behalf. Always verify details on the airline or booking site before making any purchase decisions.

## License

This project is licensed under the [Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0)](https://creativecommons.org/licenses/by-nc/4.0/).

You are free to use, modify, and share this project for non-commercial purposes. Commercial use is not permitted without explicit permission.

## Contributing

Bug reports and pull requests are welcome. Please open an [issue](https://github.com/QZJGeorge/FlightClaw/issues) to report problems or suggest improvements.
