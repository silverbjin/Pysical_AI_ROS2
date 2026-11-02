# SPDX-License-Identifier: Apache-2.0
"""One socket reader and one immutable completed frame; no ROS/model authority."""
import select
import socket
import threading
import time


class NumericReceiptInbox:
    def __init__(self,channel,read_once):
        self._channel=channel;self._read_once=read_once
        self._wake_read,self._wake_write=socket.socketpair()
        self._wake_read.setblocking(False);self._wake_write.setblocking(False)
        self._condition=threading.Condition();self._stopping=False
        self._slot=None;self._error='';self._received=None;self._tid=None
        self._started=threading.Event();self._thread=None;self._wake_closed=False

    def start(self):
        if self._thread is not None or self._stopping:raise RuntimeError('receipt reader already started or stopped')
        self._thread=threading.Thread(target=self._run,name='numeric-receipts',daemon=False)
        self._thread.start()
        if not self._started.wait(1.):raise RuntimeError('receipt reader startup deadline')

    def _run(self):
        self._tid=threading.get_native_id();self._started.set()
        try:
            while True:
                with self._condition:
                    self._condition.wait_for(lambda:self._slot is None or self._stopping)
                    if self._stopping:return
                # This callback is the existing bounded nonblocking framer.
                # A partial frame has no receipt and may never enter the slot.
                message=self._read_once()
                if message is None:
                    ready=select.select([self._channel,self._wake_read],[],[])[0]
                    if self._wake_read in ready:return
                    continue
                received=time.monotonic_ns()  # full JSON parse has completed
                with self._condition:
                    self._slot=(message,received);self._received=received
                    self._condition.notify_all()
        except Exception as error:
            with self._condition:
                self._error=repr(error);self._condition.notify_all()

    def take(self):
        with self._condition:
            if self._slot is not None:
                result=self._slot;self._slot=None;self._condition.notify_all()
                return result
            if self._error:raise ValueError('numerical receipt reader: '+self._error)
            return None

    def wait_message(self,timeout):
        """Bounded same-cycle transaction/configuration wait; no message read here."""
        with self._condition:
            self._condition.wait_for(lambda:self._slot is not None or self._error or self._stopping,timeout)
            return self._slot is not None

    def snapshot(self):
        with self._condition:
            return dict(scope='single_read_only_complete_frame_slot',tid=self._tid,
                alive=self._thread is not None and self._thread.is_alive(),
                slot_full=self._slot is not None,received_wall_ns=self._received,
                stopping=self._stopping,error=self._error)

    def stop(self,timeout):
        with self._condition:
            self._stopping=True;self._condition.notify_all()
        if not self._wake_closed:
            try:self._wake_write.send(b'x')
            except (BlockingIOError,OSError):pass
        if self._thread is not None:self._thread.join(max(0.,timeout))
        joined=self._thread is None or not self._thread.is_alive()
        if joined and not self._wake_closed:
            self._wake_read.close();self._wake_write.close();self._wake_closed=True
        return joined
