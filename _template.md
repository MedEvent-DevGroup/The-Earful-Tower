# Connector: <service name>

Brief one line description of what this credential is used for.

## Metadata

- **Service**: <e.g. HuggingFace, Asana, AWS>
- **Account**: <username or email associated>
- **Scope**: <read, write, admin, specific permissions>
- **Created**: YYYY-MM-DD
- **Expires**: YYYY-MM-DD or "never"
- **Rotated**: YYYY-MM-DD (last rotation date, blank if never)

## Credential

```
<paste the actual token, key, or secret here on its own line>
```

## Usage

Where and how this credential is consumed. Example:

- Used by `transcribe_3speakers.py` to authenticate pyannote model downloads
- Read at runtime via PowerShell: `(Select-String -Path .\connectors\<filename>.md -Pattern '<regex>').Matches.Value | Select-Object -First 1`

## Renewal

How to regenerate this credential when it expires:

1. Go to <URL>
2. Navigate to <settings path>
3. Generate new token with scope <X>
4. Replace the value in the code block above
5. Update the **Rotated** date in metadata

## Notes

Anything else worth remembering: associated team, billing implications, downstream services that break if this is rotated, etc.
