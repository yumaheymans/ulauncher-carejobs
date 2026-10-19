# ulauncher-carejobs

Search free US healthcare jobs from [Ulauncher](https://ulauncher.io/) (Linux), with the pay employers post. Nurses, CNAs, techs, therapists, medical assistants and more, from [CareJobs.Now](https://carejobs.now).

Type `cj`, a job, and a state. Press Enter to open the job.

## Install

1. Open Ulauncher Preferences, then Extensions, then Add extension.
2. Paste `https://github.com/yumaheymans/ulauncher-carejobs` and confirm.

The extension uses Ulauncher extension API v2 (`required_api_version` "2"). It needs nothing beyond Python and the libraries Ulauncher already ships with.

## Usage

| Type this | You get |
| --- | --- |
| `cj icu nurse tx` | ICU nurse jobs in Texas |
| `cj travel cna in phoenix` | Travel CNA jobs matching "phoenix" |
| `cj rn texas` | Registered nurse jobs in Texas (a full state name works too) |
| `cj remote coding` | Remote medical coding jobs |
| `cj` | A hint and five popular searches (registered nurse, CNA, LPN, medical assistant, travel nurse) |

How the text is read:

- A two-letter US state code (`tx`, `NY`) is a state when it is the last word. A full state name at the end works too (`new york`, `texas`).
- The word `remote` limits the search to remote jobs.
- A leading or trailing `in` is ignored. To search Indiana, type `indiana` in full.
- A lone `pa` or `ma` is searched as a job word (physician assistant, medical assistant), not as a state.
- Everything else is the job search.

Each result shows `Title at Employer`, then the pay (when there is one), the location and the date listed. Pay that CareJobs.Now measured from an employer's open jobs, not stated by the posting itself, is marked `typical at <employer>`.

Enter opens the job. Alt+Enter opens the employer's page on CareJobs.Now. The last result, "See all N jobs", opens the same search on the CareJobs.Now board with filters.

If CareJobs.Now cannot be reached within 8 seconds, you get one result that opens the search in your browser instead. The extension never crashes Ulauncher.

You can change the keyword (`cj`) in the extension's preferences.

## Privacy

The extension sends only what you type after the keyword (and the state or `remote` flag read from it) to `https://carejobs.now/api/mcp`, over HTTPS, to get the matching jobs. There is no account, no API key, no tracking and no analytics. Nothing is stored on your computer.

## Development

The extension is one file, `main.py`, using only the Python standard library. The search logic is plain functions (`parse_query`, `build_items`) that run without Ulauncher. To work on it, clone the repo into `~/.local/share/ulauncher/extensions/` and run `ulauncher -v` to see its output.

## License

MIT. See [LICENSE](LICENSE).
