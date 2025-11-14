#!/usr/bin/env python3
"""
NI cDAQ-9187 Relay Control Client
Controls 16 relays on 2x NI-9485 modules (Slots 2 & 3)
"""

import nidaqmx
import yaml
import threading
from pathlib import Path
from typing import Optional, Dict

# Configuration
CONFIG_PATH = Path(__file__).parent.parent / "config" / "devices.yaml"

# Global lock for thread safety
relay_lock = threading.Lock()


class RelayClient:
    """Client for controlling NI-9485 relays"""
    
    def __init__(self):
        self.config = self._load_config()
        self.device_name = self.config['devices']['NI_cDAQ']['name']
        self.slot2_config = self.config['modules']['NI_cDAQ_Relays']['slot_2']
        self.slot3_config = self.config['modules']['NI_cDAQ_Relays']['slot_3']
        self._build_relay_map()
    
    def _load_config(self):
        """Load configuration from devices.yaml"""
        with open(CONFIG_PATH, 'r') as f:
            return yaml.safe_load(f)
    
    def _build_relay_map(self):
        """Build mapping from relay names to (slot, channel)"""
        self.relay_map = {}
        
        # Slot 2 relays (RL01-RL08)
        for relay_name, relay_config in self.slot2_config.items():
            self.relay_map[relay_name] = (2, relay_config['channel'])
        
        # Slot 3 relays (RL09-RL16)
        for relay_name, relay_config in self.slot3_config.items():
            self.relay_map[relay_name] = (3, relay_config['channel'])
    
    def set_relay(self, relay_name: str, state: bool) -> bool:
        """
        Set relay state by name
        
        Args:
            relay_name: Relay name (e.g., "RL01", "RL16")
            state: True=ON, False=OFF
        
        Returns:
            True if successful, False otherwise
        """
        if relay_name not in self.relay_map:
            print(f"✗ Unknown relay: {relay_name}")
            return False
        
        slot, channel = self.relay_map[relay_name]
        return self.set_relay_by_slot_channel(slot, channel, state)
    
    def set_relay_by_slot_channel(self, slot: int, channel: int, state: bool) -> bool:
        """
        Set relay state by slot and channel
        
        Args:
            slot: Slot number (2 or 3)
            channel: Channel number (0-7)
            state: True=ON, False=OFF
        
        Returns:
            True if successful, False otherwise
        """
        with relay_lock:
            try:
                # Build channel name
                channel_name = f"{self.device_name}Mod{slot}/port0/line{channel}"
                
                # Create task and write
                with nidaqmx.Task() as task:
                    task.do_channels.add_do_chan(channel_name)
                    task.write(state)
                
                return True
            
            except Exception as e:
                print(f"✗ Failed to set relay (slot={slot}, ch={channel}): {e}")
                return False
    
    def get_relay_state(self, relay_name: str) -> Optional[bool]:
        """
        Read current relay state
        
        Args:
            relay_name: Relay name (e.g., "RL01")
        
        Returns:
            True=ON, False=OFF, None if error
        """
        if relay_name not in self.relay_map:
            return None
        
        slot, channel = self.relay_map[relay_name]
        
        with relay_lock:
            try:
                channel_name = f"{self.device_name}Mod{slot}/port0/line{channel}"
                
                with nidaqmx.Task() as task:
                    task.do_channels.add_do_chan(channel_name)
                    # Read the current state
                    state = task.read()
                
                return state
            
            except Exception as e:
                print(f"✗ Failed to read relay {relay_name}: {e}")
                return None
    
    def get_all_relay_states(self) -> Dict[str, Optional[bool]]:
        """
        Read all relay states
        
        Returns:
            Dictionary mapping relay names to states
        """
        states = {}
        for relay_name in self.relay_map.keys():
            states[relay_name] = self.get_relay_state(relay_name)
        return states
    
    def set_all_relays(self, state: bool) -> bool:
        """
        Set all relays to same state
        
        Args:
            state: True=ON, False=OFF
        
        Returns:
            True if all successful
        """
        success = True
        for relay_name in self.relay_map.keys():
            if not self.set_relay(relay_name, state):
                success = False
        return success
    
    def safe_shutdown(self) -> bool:
        """
        Set all relays to OFF (safe state)
        
        Returns:
            True if successful
        """
        print("Setting all relays to safe state (OFF)...")
        return self.set_all_relays(False)
    
    def is_device_online(self) -> bool:
        """
        Check if NI cDAQ is accessible
        
        Returns:
            True if device online
        """
        try:
            system = nidaqmx.system.System.local()
            device_names = [device.name for device in system.devices]
            return self.device_name in device_names
        except Exception:
            return False


# Convenience functions for direct use
_client = None

def get_client() -> RelayClient:
    """Get or create relay client instance"""
    global _client
    if _client is None:
        _client = RelayClient()
    return _client


def set_relay(relay_name: str, state: bool) -> bool:
    """Set relay state (convenience function)"""
    return get_client().set_relay(relay_name, state)


def get_relay_state(relay_name: str) -> Optional[bool]:
    """Get relay state (convenience function)"""
    return get_client().get_relay_state(relay_name)


def set_all_relays(state: bool) -> bool:
    """Set all relays (convenience function)"""
    return get_client().set_all_relays(state)


def safe_shutdown() -> bool:
    """Safe shutdown - all relays OFF (convenience function)"""
    return get_client().safe_shutdown()


# Test code
if __name__ == "__main__":
    print("NI Relay Control Test")
    print()
    
    client = RelayClient()
    
    # Check device
    if not client.is_device_online():
        print("✗ NI cDAQ not found")
        exit(1)
    
    print(f"✓ Found device: {client.device_name}")
    print(f"✓ Configured relays: {list(client.relay_map.keys())}")
    print()
    
    # Test relay control
    print("Testing RL01...")
    print("  Setting ON...")
    if client.set_relay("RL01", True):
        print("  ✓ Success")
        import time
        time.sleep(1)
        print("  Setting OFF...")
        if client.set_relay("RL01", False):
            print("  ✓ Success")
    
    print()
    print("Safe shutdown (all OFF)...")
    client.safe_shutdown()
    print("✓ Done")

