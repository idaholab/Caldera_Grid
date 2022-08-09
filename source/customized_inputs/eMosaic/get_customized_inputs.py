
from Caldera_global import pev_charge_ramping, supply_equipment_enum, vehicle_enum, supply_equipment_is_L1, supply_equipment_is_L2
from global_aux import container_class


def get_customized_pev_ramping():    
    
    # Ramping can NOT be defined for L1 and L2 Charging.    
    
    #=======================================
    #       ramping_by_pevType_only
    #=======================================
    
    ramping_by_pevType_only = {}
    
    #---------------------------------------------------------------------------------------
    # pev_charge_ramping -> parameters
    # off_to_on_delay_sec, off_to_on_kW_per_sec, on_to_off_delay_sec, on_to_off_kW_per_sec
    # ramp_up_delay_sec, ramp_up_kW_per_sec, ramp_down_delay_sec, ramp_down_kW_per_sec
    #---------------------------------------------------------------------------------------
    
    '''
    off_to_on_kW_per_sec = 10
    ramping_kW_per_sec = 10
    on_to_off_kW_per_sec = -140000    
    X = pev_charge_ramping(15, off_to_on_kW_per_sec, 0.05, on_to_off_kW_per_sec, 0.1, ramping_kW_per_sec, 0.1, -ramping_kW_per_sec)
    ramping_by_pevType_only[vehicle_enum.ld_50kWh] = X
    
    off_to_on_kW_per_sec = 10
    ramping_kW_per_sec = 10
    on_to_off_kW_per_sec = -140000
    X = pev_charge_ramping(15, off_to_on_kW_per_sec, 0.05, on_to_off_kW_per_sec, 0.1, ramping_kW_per_sec, 0.1, -ramping_kW_per_sec)
    ramping_by_pevType_only[vehicle_enum.ld_100kWh] = X
    
    off_to_on_kW_per_sec = 25
    ramping_kW_per_sec = 25
    on_to_off_kW_per_sec = -140000
    X = pev_charge_ramping(15, off_to_on_kW_per_sec, 0.05, on_to_off_kW_per_sec, 0.1, ramping_kW_per_sec, 0.1, -ramping_kW_per_sec)
    ramping_by_pevType_only[vehicle_enum.md_200kWh] = X

    off_to_on_kW_per_sec = 25    
    ramping_kW_per_sec = 25
    on_to_off_kW_per_sec = -140000
    X = pev_charge_ramping(15, off_to_on_kW_per_sec, 0.05, on_to_off_kW_per_sec, 0.1, ramping_kW_per_sec, 0.1, -ramping_kW_per_sec)
    ramping_by_pevType_only[vehicle_enum.hd_300kWh] = X

    off_to_on_kW_per_sec = 40    
    ramping_kW_per_sec = 40
    on_to_off_kW_per_sec = -140000
    X = pev_charge_ramping(15, off_to_on_kW_per_sec, 0.05, on_to_off_kW_per_sec, 0.1, ramping_kW_per_sec, 0.1, -ramping_kW_per_sec)
    ramping_by_pevType_only[vehicle_enum.hd_400kWh] = X

    off_to_on_kW_per_sec = 40    
    ramping_kW_per_sec = 40
    on_to_off_kW_per_sec = -140000
    X = pev_charge_ramping(15, off_to_on_kW_per_sec, 0.05, on_to_off_kW_per_sec, 0.1, ramping_kW_per_sec, 0.1, -ramping_kW_per_sec)
    ramping_by_pevType_only[vehicle_enum.hd_600kWh] = X
    '''

    #=======================================
    #       ramping_by_pevType_seType
    #=======================================
    
    ramping_by_pevType_seType = {}
    
    '''
    off_to_on_kW_per_sec = 25
    on_to_off_kW_per_sec = -140000
    ramping_kW_per_sec = 25
    X = pev_charge_ramping(15, off_to_on_kW_per_sec, 0.05, on_to_off_kW_per_sec, 0.1, ramping_kW_per_sec, 0.1, -ramping_kW_per_sec)
    ramping_by_pevType_seType[(vehicle_enum.ld_50kWh, supply_equipment_enum.xfc_500)] = X
    '''

    #=========================================
    #          Checking Parameters
    #=========================================
    
    is_valid = True
    
    for (pev_type, Y) in ramping_by_pevType_only.items():
        if Y.off_to_on_delay_sec <= 0:
            is_valid = False
            print('Invalid ramping_by_pevType_only parameter off_to_on_delay_sec.  pev_type: {}'.format(pev_type))
        
        if Y.off_to_on_kW_per_sec <= 0:
            is_valid = False
            print('Invalid ramping_by_pevType_only parameter off_to_on_kW_per_sec.  pev_type: {}'.format(pev_type))
        
        if not(0 < Y.on_to_off_delay_sec and Y.on_to_off_delay_sec <= 0.2):
            is_valid = False
            print('Invalid ramping_by_pevType_only parameter on_to_off_delay_sec.  pev_type: {}'.format(pev_type))
            
        if -6000 <= Y.on_to_off_kW_per_sec:
            is_valid = False
            print('Invalid ramping_by_pevType_only parameter on_to_off_kW_per_sec.  pev_type: {}'.format(pev_type))
            
        if Y.ramp_up_delay_sec <= 0:
            is_valid = False
            print('Invalid ramping_by_pevType_only parameter ramp_up_delay_sec.  pev_type: {}'.format(pev_type))
            
        if Y.ramp_up_kW_per_sec < 10:
            is_valid = False
            print('Invalid ramping_by_pevType_only parameter ramp_up_kW_per_sec.  pev_type: {}'.format(pev_type))
        
        if Y.ramp_down_delay_sec <= 0:
            is_valid = False
            print('Invalid ramping_by_pevType_only parameter ramp_down_delay_sec.  pev_type: {}'.format(pev_type))
            
        if Y.ramp_down_kW_per_sec > -10:
            is_valid = False
            print('Invalid ramping_by_pevType_only parameter ramp_down_kW_per_sec.  pev_type: {}'.format(pev_type))
            
        if not is_valid:
            break
    
    if is_valid:
        for ((pev_type, se_type), Y) in ramping_by_pevType_seType.items():
            if supply_equipment_is_L1(se_type) or supply_equipment_is_L2(se_type):
                is_valid = False
                print('Ramping can NOT be specified for L1 and L2 charging.  pev_type: {}  se_type: {}'.format(pev_type, se_type))
            
            if Y.off_to_on_delay_sec <= 0:
                is_valid = False
                print('Invalid ramping_by_pevType_seType parameter off_to_on_delay_sec.  pev_type: {}  se_type: {}'.format(pev_type, se_type))
            
            if Y.off_to_on_kW_per_sec <= 0:
                is_valid = False
                print('Invalid ramping_by_pevType_seType parameter off_to_on_kW_per_sec.  pev_type: {}  se_type: {}'.format(pev_type, se_type))
            
            if Y.on_to_off_delay_sec <= 0:
                is_valid = False
                print('Invalid ramping_by_pevType_seType parameter on_to_off_delay_sec.  pev_type: {}  se_type: {}'.format(pev_type, se_type))
                
            if Y.on_to_off_kW_per_sec >= 0:
                is_valid = False
                print('Invalid ramping_by_pevType_seType parameter on_to_off_kW_per_sec.  pev_type: {}  se_type: {}'.format(pev_type, se_type))
                
            if Y.ramp_up_delay_sec <= 0:
                is_valid = False
                print('Invalid ramping_by_pevType_seType parameter ramp_up_delay_sec.  pev_type: {}  se_type: {}'.format(pev_type, se_type))
                
            if Y.ramp_up_kW_per_sec < 10:
                is_valid = False
                print('Invalid ramping_by_pevType_seType parameter ramp_up_kW_per_sec.  pev_type: {}  se_type: {}'.format(pev_type, se_type))
            
            if Y.ramp_down_delay_sec <= 0:
                is_valid = False
                print('Invalid ramping_by_pevType_seType parameter ramp_down_delay_sec.  pev_type: {}  se_type: {}'.format(pev_type, se_type))
                
            if Y.ramp_down_kW_per_sec > -10:
                is_valid = False
                print('Invalid ramping_by_pevType_seType parameter ramp_down_kW_per_sec.  pev_type: {}  se_type: {}'.format(pev_type, se_type))
            
            if not is_valid: 
                break
    
    #=========================================
    #            Return Results
    #=========================================
    
    customized_pev_ramping = container_class()
    customized_pev_ramping.ramping_by_pevType_only = ramping_by_pevType_only
    customized_pev_ramping.ramping_by_pevType_seType = ramping_by_pevType_seType
    
    return (is_valid, customized_pev_ramping)
    