from datetime import datetime

end_time_timestamp = int("0x5cdc334963583", 16) / 1000000
end_time = datetime.fromtimestamp(end_time_timestamp) #.strftime('%Y-%m-%d %H:%M:%S')
now_time = datetime.now()
seconds_in_day = 24 * 60 * 60

diff = end_time - now_time
duration_in_s = diff.total_seconds()

#print(end_time, diff.seconds)
print("Difference:", diff)
print("Days:", diff.days)
print("Microseconds:", diff.microseconds)
print("Seconds:", diff.seconds)
print("total seconds: ", diff.total_seconds() / 3600.0)

hours = divmod(duration_in_s, 3600)        # Get days (without [0]!)
minutes = divmod(hours[1], 60)                # Use remainder of hours to calc minutes
seconds = divmod(minutes[1], 1)               # Use remainder of minutes to calc seconds
print("Duration: %dh %dm left" % (hours[0], minutes[0]))

duration = "%dh %dm left" % (hours[0], minutes[0])
print("duration:", duration)

print("Time between dates: %d hours, %d minutes and %d seconds" % (hours[0], minutes[0], seconds[0]))

days = divmod(duration_in_s, 86400)        # Get days (without [0]!)
hours   = divmod(days[1], 3600)               # Use remainder of days to calc hours
minutes = divmod(hours[1], 60)                # Use remainder of hours to calc minutes
seconds = divmod(minutes[1], 1)               # Use remainder of minutes to calc seconds
print("Time between dates: %d days, %d hours, %d minutes and %d seconds" % (days[0], hours[0], minutes[0], seconds[0]))

