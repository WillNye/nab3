# Change Log

---

# 0.1.4 (2020/10/06)

### Bug Fixes
* Standardizing response on a list of dicts that hit on a service

### Features
* Optional force argument to manually reload an object and related attrs e.g. `asg_resp.fetch('security_groups', force=True)`

---

# 0.1.2 (2020/09/30)

### Bug Fixes
* No longer fetching instances when calling ASG.fetch('pricing')
* Fix bad response from the Pricing.load_pricing when pricing is already loaded
* Remove default None in getattr within Filter._match

### Features
* None

---

# 0.1.1 (2020/09/28)

### Bug Fixes
* Cleaned up README
* Added an interval argument to `set_service_stats` and `set_n_service_stats`

### Features
* Added support for `ECSCluster.security_groups`
* Created a `PricingMixin`
* Pricing support added to:
  * `EC2Instance` 
  * `ASG` 
  * `ECSCluster` 

---

# 0.1.0 (2020/09/22)

### Bug Fixes
* None

### Features
* Initial Release
