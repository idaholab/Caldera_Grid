import helics as h
import pickle

pickle_protocol = pickle.HIGHEST_PROTOCOL

def chunk_generator(bytes, chunk_size):
    for i in range(0, len(bytes), chunk_size):
        yield bytes[i:i+chunk_size]

def send(dataset, endpoint_local, endpoint_remote):
    chunk_size = 10000000
    bytes = pickle.dumps(dataset, protocol=pickle_protocol)
    for chunk in chunk_generator(bytes, chunk_size):
        h.helicsEndpointSendBytesTo(endpoint_local, chunk, endpoint_remote)

def receive(endpoint_local):
    tmp = {}
    while h.helicsEndpointHasMessage(endpoint_local):
        msg = h.helicsEndpointGetMessage(endpoint_local)
        bytes = h.helicsMessageGetBytes(msg)
        source_str = h.helicsMessageGetSource(msg)
        
        if source_str not in tmp:
            tmp[source_str] = bytearray()
            
        tmp[source_str].extend(bytes)
    
    return_val = {}
    for (source_str, bytes) in tmp.items():
        return_val[source_str] = pickle.loads(bytes)
        
    return return_val

def cleanup(fed):
    h.helicsFederateDisconnect(fed)
    h.helicsFederateFree(fed)
    h.helicsCloseLibrary()