@echo off
rem Creates two daily Windows scheduled tasks (07:00 and 19:00 local time) for the current user.
set RUN=%~dp0run_local.cmd
schtasks /Create /TN "Mikser-07" /TR "\"%RUN%\" morning" /SC DAILY /ST 07:00 /F
schtasks /Create /TN "Mikser-19" /TR "\"%RUN%\" evening" /SC DAILY /ST 19:00 /F
schtasks /Query /TN "Mikser-07" /FO LIST | findstr /i "TaskName Next"
schtasks /Query /TN "Mikser-19" /FO LIST | findstr /i "TaskName Next"
