# Unicorn Properties: Properties Web

## Overview

TODO: add overview

TODO: add architecture image

## Testing with Postman

TODO: add instructions

## Testing with TODO: curl or httpie

Using Httpie as a starting point; will need to change to Postman next

### Add

```bash
https https://rruhykpqtb.execute-api.ap-southeast-1.amazonaws.com/default/properties/add < postman/property01.json
```

### List property by city and by street

```bash
https https://rruhykpqtb.execute-api.ap-southeast-1.amazonaws.com/default/properties/list/usa/anytown
https https://rruhykpqtb.execute-api.ap-southeast-1.amazonaws.com/default/properties/list/usa/anytown/main-street
```

### Property details

```bash
https https://rruhykpqtb.execute-api.ap-southeast-1.amazonaws.com/default/properties/usa/anytown/main-street/123
```
