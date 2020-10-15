# Change Log
---

# 0.1.6 (2020/10/14)

### Bug Fixes
* Updated Service.load methods to include force param
* Cleaned up Passing force to Service.load methods
* Updated ServiceWrapper.__setattr__ to properly set service attributes
* Fix issue when calling a ServiceWrapper.service.list if the service had already been loaded
* Fix issue where ServiceWrapper wasn't passing the load param to the Service class

### Features
* None

---

# 0.1.5 (2020/10/14)

### Bug Fixes
* ServiceWrapper.is_list now public instead of protected
* Fixed Filter._match behavior on nested service lookups 
* Iterating a list of Service objects now properly yielding with the ServiceWrapper 

### Features
* Created an account property within the ClientHandler to return the account id for the current session
* Added the EC2 Image service


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
