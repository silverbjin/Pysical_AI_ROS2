"""Scoped temporary lease for the explicitly approved shared-clock comparison."""
class ClockLease:
    DISTROS=('Ubuntu-22.04','Ubuntu-24.04')
    def __init__(self, ops, save, *, normalize_tick=True):
        self.ops,self.save,self.normalize_tick=ops,save,normalize_tick
        self.record={'restoration_pending':False,'restored':False,'errors':[],
                     'attempted_services':[],'tick_write_attempted':False}
    def persist(self):self.save(self.record)
    def begin(self):
        initial={d:self.ops.inspect(d) for d in self.DISTROS}
        clock=self.ops.clock()
        tick_ok=(clock['tick_us']==9166 if self.normalize_tick else
                 type(clock['tick_us']) is int and 9000<=clock['tick_us']<=11000)
        if any(v['active']!='active' or v['clock_ticks']!=100
               or v['boot']!=clock['boot_id'] or v['namespace']!=initial[self.DISTROS[0]]['namespace']
               for v in initial.values()) or not tick_ok:
            raise RuntimeError('initial environment differs from approved observation; no mutation')
        self.record.update(initial_services=initial,initial_clock=clock,restoration_pending=True)
        self.persist()
        for d in self.DISTROS:
            self.record['attempted_services'].append(d);self.persist()
            self.ops.service(d,'stop')
            if self.ops.inspect(d)['active']!='inactive':raise RuntimeError('service did not stop')
        if not self.normalize_tick:
            self.record['tick_restoration_scope']='not_modified_by_this_lease'
            self.persist();return self.record
        self.record['tick_write_attempted']=True;self.persist()
        self.ops.set_tick(9166,10000,clock['boot_id'])
        normalized=self.ops.clock()
        if normalized['tick_us']!=10000 or normalized['boot_id']!=clock['boot_id']:
            raise RuntimeError('temporary tick not confirmed')
        self.record['normalized_clock']=normalized;self.persist()
        return self.record
    def close(self):
        initial=self.record.get('initial_clock')
        if initial is None:
            self.record.update(restored=True,restoration_pending=False,restoration_scope='no_mutation_attempted')
            self.persist();return True
        try:
            clock=self.ops.clock()
            if clock['boot_id']!=initial['boot_id']:
                raise RuntimeError('boot identity changed; no operation on replacement instance')
        except BaseException as error:
            self.record['errors'].append(repr(error));self.persist();return False
        tick_ok=not self.record['tick_write_attempted']
        if self.record['tick_write_attempted']:
            try:
                if clock['tick_us']==10000:
                    self.ops.set_tick(10000,initial['tick_us'],initial['boot_id'])
                elif clock['tick_us']!=initial['tick_us']:
                    raise RuntimeError('external tick writer; do not overwrite unknown value')
                tick_ok=self.ops.clock()['tick_us']==initial['tick_us']
                if not tick_ok:raise RuntimeError('tick restoration unconfirmed')
            except BaseException as error:self.record['errors'].append(repr(error))
            self.record['tick_restored']=tick_ok;self.persist()
        services_ok=True
        for d in reversed(self.record['attempted_services']):
            try:
                before=self.ops.inspect(d)
                if before['boot']!=initial['boot_id']:raise RuntimeError('service instance changed')
                expected=self.record['initial_services'][d]
                if (expected.get('init_start_ticks') is not None
                        and before.get('init_start_ticks')!=expected['init_start_ticks']):
                    raise RuntimeError('distro init identity changed; do not operate on replacement')
                self.ops.service(d,'start')
                after=self.ops.inspect(d)
                if (after['active'],after['enabled'])!=(expected['active'],expected['enabled']):
                    raise RuntimeError('service restoration mismatch: '+d)
            except BaseException as error:
                services_ok=False;self.record['errors'].append(repr(error))
            self.persist()
        self.record['services_restored']=services_ok
        self.record['restored']=tick_ok and services_ok and not self.record['errors']
        self.record['restoration_pending']=not self.record['restored'];self.persist()
        return self.record['restored']
