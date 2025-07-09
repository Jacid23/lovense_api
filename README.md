# Lovense Standard API Integration

A Home Assistant custom integration for controlling Lovense devices using the official Standard API.

## Features

- **Voice Control**: "Hey Google, set bedroom light to 80%"
- **Complete Device Control**: Vibration intensity (0-20) + Position control (0-100)
- **Official API**: Direct Lovense Standard API integration
- **Stable Entities**: Persistent across reboots
- **Multiple Devices**: Supports Solace Pro, Max, Nora, Lush, Edge, Domi

## Installation

### Via HACS (Recommended)
1. Add this repository to HACS as a custom repository
2. Install through HACS
3. Restart Home Assistant
4. Add integration through Settings → Integrations

### Manual Installation
1. Copy `custom_components/lovense_api` to your HA `custom_components` directory
2. Restart Home Assistant
3. Add integration through Settings → Integrations

## Configuration

- **Developer Token**: Get from [Lovense Developer Dashboard](https://www.lovense.com/user/developer/info)
- **Callback URL**: `http://YOUR_HA_IP:8123/api/lovense/callback`
- **User ID**: Any unique identifier for your account

## Setup Process

1. Configure the integration with your API token and callback URL
2. QR code will be generated
3. Scan QR code with Lovense Remote app
4. Devices will appear as entities in Home Assistant

## Entities Created

### Light Entity
- Primary control with voice support
- Vibration intensity control (0-100%)
- Preset effects (pulse, wave, fireworks, earthquake)

### Number Entity (Solace Pro)
- Precise position control (0-100)
- Stroker position adjustment

### Sensor Entities
- Battery level percentage
- Connection status

## 🔒 Security & Callback URL

**⚠️ NEVER expose Home Assistant directly to the internet!**

For the callback URL requirement, use one of these **secure** options:

### Option 1: Cloudflare Tunnel (FREE, Recommended)
```bash
# Download cloudflared, then run:
cloudflared tunnel --url http://localhost:8123

# Use the generated URL like:
https://random-words.trycloudflare.com/api/lovense/callback
```

### Option 2: Nabu Casa ($6/month, Easiest)
```
https://your-id.ui.nabu.casa/api/lovense/callback
```

### Option 3: Tailscale VPN (Most Secure)
```
http://100.64.x.x:8123/api/lovense/callback
```

**Never use direct port forwarding or expose HA to the internet!**

## Voice Control Examples

- "Hey Google, turn on bedroom light"
- "Hey Google, set bedroom light to 75%"
- "Hey Google, turn off bedroom light"

## Support

- [Official Lovense API Documentation](https://developer.lovense.com/docs/standard-solutions/standard-api.html)
- [Home Assistant Integration Documentation](https://developers.home-assistant.io/)

## License

MIT License - See LICENSE file for details.
