# Ping
A Docker image that pings a number of ip adresses.
## Usage
Run:
```bash
docker run --rm -e HOST_LIST='192.168.178.1' ghcr.io/fsteltenkamp/ping:latest
```
Compose:
```yaml
services:
  ping:
    image: ghcr.io/fsteltenkamp/ping:latest
    volumes:
      - /some/path:/ping
    environment:
      - INTERVAL=10
      - PING_COUNT=10
      - INFLUXDB_HOST=https://some.influxdb.host
      - INFLUXDB_ORG=Your Org
      - INFLUXDB_TOKEN=token
      - INFLUXDB_TIMEOUT=6000
      - INFLUXDB_VERIFY_SSL=true
      - URL=your.app/whatever/path/you/made
      - API_TOKEN=api_token
      - HOST_LIST='192.168.178.1,192.168.178.2'
      - HOSTS_FILE=devices.json
```
## Volumes:
- `/ping_script`: The Script is located here.  
DO NOT MOUNT TO THIS DIRECTORY, unless you want to change the script itself.  
- `/ping`: Your Data should be located here. Put anything you want in here.
The script will look up any file thats referenced in this directory.
## Available Environment Variables:
- `DEBUG`: If true, script prints debug messages.
- `INTERVAL`: (Seconds) This Variable defines the time that the Script waits in between runs.
Since the Amount of time a run takes is dependent on how many hosts there are to ping, its not realistic to set a fixed interval.
This is the second best way to do it i think. (If you have a better idea, open an issue.)
- `PING_COUNT`: How many pings per host should be done. IMO 10 is good to get an accurate average.  
If you have a larger list of hosts to ping, maybe lower this number.
- `SRC_HOST_NAME: A Descriptive name for the source of this ping. Very useful if you run pings from different sources and want to be able to tell the results apart.  
This is set in the influxdb data as a tag 'src'.
- `INFLUXDB_URL`: URL Of a InfluxDB2 Instance you want the results stored on.
- `INFLUXDB_ORG`: The Org on the InfluxDB Instance.
- `INFLUXDB_TOKEN`: Token.
- `INFLUXDB_BUCKET`: Bucket
- `INFLUXDB_TIMEOUT:` idk.
- `INFLUXDB_VERIFY_SSL:` Set to False if you need to use a selfsigned cert or sth like that.
- `URL`: A Url of an API that provides the list of hosts to ping. See [Ping Api Format](#ping-api-format) for information on how to structure the data on that api endpoint.
- `API_TOKEN`: Api Token for that Url. Used as a "Bearer" Token.
- `HOSTS_FILE`: Alternative way to provide a list of hosts to the script.  
if this is used, `URL`, `API_TOKEN` and `HOST_LIST` should not be set.  
This should contain the same structure as the api endpoint. see [Ping Api Format](#ping-api-format) for reference.
- `HOST_LIST`: Alternative way to provide a list of hosts to the script.  
if this is used, `URL`, `API_TOKEN` and `HOSTS_FILE` should not be set.  
List should be a comma separated string of ip addresses.

### Ping Api Format
It is expected that the data follows the following structure, provided as JSON on the request Body:
```json
{
  "devices": [
    {
      "publicIp": 127.0.0.1,
    },
    {
      "publicIp": 127.0.0.1
    }
  ]
}
```
The association from the device to whatever you want to display is up to you.  
Every Device is unique by its IP Address. meaning multiple hosts using the same IP Address are not supported.  
That would'nt make sense anyways.