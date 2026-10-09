# Troubleshooting Guide

Common issues and solutions for the OpenStack review skill.

## Vertex AI Issues

### Error: "missing required dependency `google-cloud-aiplatform`"

**Problem:** The `anthropic` package doesn't have Vertex AI dependencies installed.

**Solution:**
```bash
pip install 'anthropic[vertex]'
```

Or install all dependencies:
```bash
pip install claude-agent-sdk 'anthropic[vertex]'
```

### No models detected or all models show errors

**Problem:** Models aren't available or there's a configuration issue.

**Solution:** Check your region configuration:
```bash
# Use your organization's required region (default is 'global')
python detect_models.py --vertex --project YOUR_PROJECT --region global

# Or use a specific region if required by your org
python detect_models.py --vertex --project YOUR_PROJECT --region us-central1
```

**Common regions:**
- `global` (default, uses Google's global endpoint)
- `us-central1`
- `europe-west1`
- `asia-southeast1`

**Note:** Use the region specified by your organization's policy.

### Error: "DefaultCredentialsError" or "Could not automatically determine credentials"

**Problem:** Not authenticated with Google Cloud.

**Solution:**
```bash
gcloud auth application-default login
```

### Error: "Permission denied" or "403 Forbidden"

**Problem:** Your account doesn't have Vertex AI permissions.

**Solution:** Ask your Google Cloud admin to grant these IAM roles:
- `roles/aiplatform.user` (to use Vertex AI)

Or grant them yourself if you have admin access:
```bash
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="user:YOUR_EMAIL@example.com" \
  --role="roles/aiplatform.user"
```

### Error: "API not enabled" or "Service ... is not enabled"

**Problem:** Vertex AI API is not enabled for your project.

**Solution:**
```bash
gcloud services enable aiplatform.googleapis.com --project=YOUR_PROJECT_ID
```

### All models show "Model not found" or "No permission"

**Possible causes:**
1. **Wrong region** - Claude models aren't available in all regions
   - Try `--region us-east5`
2. **API not enabled** - Enable Vertex AI API (see above)
3. **No permissions** - Need `roles/aiplatform.user`
4. **Models not available** - Some GCP organizations restrict model access
   - Contact your GCP admin to enable Claude models

## Anthropic API Issues

### Error: "ANTHROPIC_API_KEY environment variable not set"

**Problem:** API key not configured.

**Solution:**
```bash
export ANTHROPIC_API_KEY=your-api-key-here
```

Add to your `~/.bashrc` or `~/.zshrc` to make it permanent:
```bash
echo 'export ANTHROPIC_API_KEY=your-api-key-here' >> ~/.bashrc
source ~/.bashrc
```

### Error: "Invalid API key" or "401 Unauthorized"

**Problem:** API key is incorrect or expired.

**Solution:**
1. Check your API key at https://console.anthropic.com/
2. Generate a new key if needed
3. Update your environment variable

### Error: "Model not found" for all models

**Possible causes:**
1. **Enterprise plan restrictions** - Your plan may not include all models
   - Run `python detect_models.py` to see available models
2. **Model name changed** - Model IDs may have been updated
   - Check latest model IDs in documentation

## Installation Issues

### Error: "No module named 'anthropic'"

**Problem:** `anthropic` package not installed.

**Solution:**
```bash
pip install anthropic
```

Or for Vertex AI:
```bash
pip install 'anthropic[vertex]'
```

### Error: "No module named 'claude_agent_sdk'"

**Problem:** Claude Agent SDK not installed.

**Solution:**
```bash
pip install claude-agent-sdk
```

### Error: "No module named 'google.auth'" or "No module named 'google.cloud.aiplatform'"

**Problem:** Google Cloud dependencies not installed (Vertex AI only).

**Solution:**
```bash
pip install 'anthropic[vertex]'
```

Or install separately:
```bash
pip install google-auth google-cloud-aiplatform
```

## Review Agent Issues

### Error: "review_config not found" or "get_model_config not found"

**Problem:** Missing or corrupted `review_config.py`.

**Solution:**
1. Make sure `review_config.py` exists in the same directory as `review_agent.py`
2. If missing, copy from `review_config.example.py`:
   ```bash
   cp review_config.example.py review_config.py
   ```

### Review hits turn limit before finishing

**Problem:** Complex review needs more turns.

**Solutions:**
1. Use a preset with more turns:
   ```bash
   python review_agent.py 970404 --preset thorough
   ```

2. Use a more capable model:
   ```bash
   python review_agent.py 970404 --model claude-opus-5
   ```

3. Edit `review_config.py` and increase `max_turns` for your preset

### Review fails with "Rate limit exceeded"

**Problem:** Too many API requests.

**Solutions:**
1. Wait a few minutes and retry
2. Use a lower-tier model (Haiku instead of Opus)
3. For Vertex AI: Check your quota in Google Cloud Console

## Gerrit Issues

### Error: "Could not fetch review" or ".gitreview not found"

**Problem:** Not in a Git repository or `.gitreview` file missing.

**Solution:**
1. Make sure you're in an OpenStack project directory
2. Check if `.gitreview` exists:
   ```bash
   ls -la .gitreview
   ```
3. If missing, this skill only works with OpenStack projects that use Gerrit

### Error: "Review not found" or "404"

**Problem:** Invalid review number or wrong Gerrit host.

**Solutions:**
1. Verify the review number in browser
2. Specify Gerrit host explicitly:
   ```bash
   python review_agent.py 970404 --gerrit-host review.opendev.org
   ```

## General Debugging

### Enable verbose output

For more detailed error messages:

1. **detect_models.py:**
   ```bash
   python detect_models.py --verbose
   ```

2. **Python errors:**
   ```bash
   python -v review_agent.py 970404
   ```

3. **Bash debugging:**
   ```bash
   bash -x gerrit_review.py fetch 970404
   ```

### Check versions

```bash
pip list | grep -E "(anthropic|claude|google)"
python --version
gcloud --version
```

### Test minimal setup

Test if basic Anthropic/Vertex AI works:

**Anthropic API:**
```python
from anthropic import Anthropic
client = Anthropic()
response = client.messages.create(
    model="claude-sonnet-4-5",
    max_tokens=10,
    messages=[{"role": "user", "content": "Hi"}]
)
print(response.content)
```

**Vertex AI:**
```python
from anthropic import AnthropicVertex
client = AnthropicVertex(project_id="YOUR_PROJECT", region="us-east5")
response = client.messages.create(
    model="claude-3-5-sonnet-v2@20241022",
    max_tokens=10,
    messages=[{"role": "user", "content": "Hi"}]
)
print(response.content)
```

## Still Having Issues?

1. Check the logs in `output.log` if it exists
2. Review the specific error message carefully
3. Consult the relevant guide:
   - [VERTEX_AI_SETUP.md](VERTEX_AI_SETUP.md) for Vertex AI
   - [MODEL_CONFIGURATION.md](MODEL_CONFIGURATION.md) for model config
   - [QUICKSTART.md](QUICKSTART.md) for setup steps
4. Open an issue on GitHub with:
   - Full error message
   - Command you ran
   - Python version
   - Output of `pip list | grep -E "(anthropic|claude|google)"`
