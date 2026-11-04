# Backend

One Python monolith for VitalWatch.

It will own login, care homes, patients, staff, devices, readings, vitals checks, movement checks, and alerts. [admin-portal](../admin-portal/README.md), [caregiver-app](../caregiver-app/README.md), and the devices all talk to this service.

Domain code will live in this folder as modules when each part is built.
