import zeep
import logging.config

# Enable detailed logging for Zeep
logging.config.dictConfig({
    'version': 1,
    'formatters': {
        'verbose': {
            'format': '%(name)s: %(message)s'
        }
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'zeep': {
            'level': 'DEBUG',
            'propagate': True,
            'handlers': ['console'],
        },
    }
})

# WSDL URL
wsdl = "https://newmarkets.transelectrica.ro/usy-durom-wsendpointg01/00121002300000000000000000000100/ws?wsdl"

# Create Zeep client
client = zeep.Client(wsdl=wsdl)

# Print available service methods
for service in client.wsdl.services.values():
    for port in service.ports.values():
        operations = sorted(port.binding._operations.values(), key=lambda operation: operation.name)
        for operation in operations:
            print(f"Operation: {operation.name}")
            print(f"  Input: {operation.input.signature()}")
            print(f"  Output: {operation.output.signature()}")
