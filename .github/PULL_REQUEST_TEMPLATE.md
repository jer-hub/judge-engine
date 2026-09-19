## Description

Briefly describe what this PR does and why.

Fixes #(issue number, if applicable)

## Type of Change

- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to change)
- [ ] Documentation update

## Testing

How have you tested this change?

### Backend Tests
```bash
docker compose exec backend python manage.py test
```
- [ ] All tests pass locally
- [ ] Added new tests for this change (if applicable)
- [ ] Coverage maintained or improved

### Frontend Tests
```bash
docker compose exec frontend npm run test
```
- [ ] Builds successfully (`npm run build`)
- [ ] Works on desktop
- [ ] Works on tablet (if UI changes)

## Checklist

- [ ] My code follows the project's code style
- [ ] I have updated documentation (README, CONTRIBUTING, etc.) if needed
- [ ] I have not introduced any hardcoded secrets or sensitive data
- [ ] I have tested this locally with Docker Compose
- [ ] I have added/updated tests if this is a feature or bug fix
- [ ] No new warnings or errors introduced

## Screenshots (if applicable)

If this PR changes the UI, add before/after screenshots:

### Before


### After


## Deployment Notes

Any special steps needed to deploy this? (migrations, new env vars, etc.)

---

Thank you for contributing! 🎓
