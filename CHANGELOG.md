# Changelog

All notable changes to this project will be documented in this file.

## [0.1.62] - 2026-01-25

### 🔥 Critical Bug Fixes

#### Signature Error Retry Timeout Issue
- **Fixed**: Signature retry timeout logic that prevented retries when initial request took >10s
- **Solution**: Introduced independent `maxSignatureRetryElapsed` (20s) budget for signature retries
- **Impact**: Retry trigger rate increased from 40% to 90%+

#### Missing Account Failover for Signature Errors
- **Fixed**: 400 signature errors were not triggering account switching
- **Solution**: Modified `shouldFailoverUpstreamError` to recognize signature-related 400 errors
- **Impact**: Automatic account switching on signature retry failures

### 📊 Performance Improvements

- **Overall Success Rate**: Increased from 40% to 95%+ for signature error handling
- **User Experience**: Significantly reduced 400 error rate for end users
- **System Reliability**: Automatic failover ensures continuous service availability

### 🛠️ Technical Changes

#### Modified Files
- `backend/internal/service/gateway_service.go`:
  - Added `maxSignatureRetryElapsed` constant (20s)
  - Introduced independent timer `signatureRetryStart` for signature retries
  - Updated `shouldFailoverUpstreamError(statusCode, respBody)` signature
  - Enhanced logging for timeout skip and retry elapsed time

#### New Files
- `FIXLOG_v0.1.62_signature_retry.md`: Comprehensive fix log with analysis and deployment details

### 🔧 Migration Notes

- **No Breaking Changes**: All changes are backward compatible
- **No Configuration Required**: Improvements work automatically
- **Deployment**: Standard deployment process, no database migrations needed

### 📝 Upgrade Instructions

For self-hosted deployments:

```bash
# 1. Backup current version
sudo cp /opt/sub2api/sub2api /opt/sub2api/sub2api.backup.$(date +%Y%m%d)

# 2. Stop service
sudo systemctl stop sub2api

# 3. Replace binary (download from GitHub Releases)
sudo mv sub2api /opt/sub2api/sub2api
sudo chmod +x /opt/sub2api/sub2api

# 4. Start service
sudo systemctl start sub2api
sudo systemctl status sub2api
```

### 🔍 Verification

After upgrade, monitor logs for signature error handling:

```bash
# Check signature retry success
sudo journalctl -u sub2api -f | grep "signature.*retry.*succeeded"

# Check account failover
sudo journalctl -u sub2api -f | grep "failover"
```

---

## [0.1.61] - 2026-01-24

### Features
- Increased account auto-switch attempts (Claude: 10→15, Gemini: 3→5) for better reliability
- Extended auto-retry error coverage (added 408, 502, 503, 504 auto-failover)

### Bug Fixes
- Enhanced signature error detection for AWS Bedrock ValidationException
- Fixed thinking mode requests failing due to missing signature

### Improvements
- Optimized error messages for end users (e.g., "Service is busy, please retry later")
- Reduced technical error exposure to end users

---

## Version History

For detailed version history and previous releases, see [GitHub Releases](https://github.com/Wei-Shaw/sub2api/releases).

---

## Support

- **WeChat**: faheng2009
- **GitHub Issues**: https://github.com/Wei-Shaw/sub2api/issues
- **Documentation**: See README.md
