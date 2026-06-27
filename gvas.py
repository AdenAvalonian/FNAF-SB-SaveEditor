"""gvas.py - Generic GVAS (Unreal Engine SaveGame) parser/serializer.
Round-trips FNAF:SB SaveGameSlotN.sav (UE4.27) byte-for-byte. Stdlib only."""
import struct

BINARY_STRUCT_TYPES = {
    "Vector","Rotator","Vector2D","Quat","Guid","DateTime","Timespan",
    "Color","LinearColor","IntPoint","Transform","Box","Box2D","IntVector","Vector4",
}

class GvasError(Exception): pass

class Reader:
    def __init__(self,data): self.d=data; self.p=0
    def remaining(self): return len(self.d)-self.p
    def bytes(self,n):
        if self.p+n>len(self.d): raise GvasError(f"read past end: want {n} at {self.p}")
        b=self.d[self.p:self.p+n]; self.p+=n; return b
    def i32(self): v=struct.unpack_from("<i",self.d,self.p)[0]; self.p+=4; return v
    def u32(self): v=struct.unpack_from("<I",self.d,self.p)[0]; self.p+=4; return v
    def i64(self): v=struct.unpack_from("<q",self.d,self.p)[0]; self.p+=8; return v
    def u16(self): v=struct.unpack_from("<H",self.d,self.p)[0]; self.p+=2; return v
    def f32(self): v=struct.unpack_from("<f",self.d,self.p)[0]; self.p+=4; return v
    def u8(self): v=self.d[self.p]; self.p+=1; return v
    def fstring(self):
        n=self.i32()
        if n==0: return ""
        if n>0: return self.bytes(n)[:-1].decode("latin1")
        n=-n; return self.bytes(n*2)[:-2].decode("utf-16-le")

class Writer:
    def __init__(self): self.buf=bytearray()
    def bytes(self,b): self.buf+=b
    def i32(self,v): self.buf+=struct.pack("<i",v)
    def u32(self,v): self.buf+=struct.pack("<I",v)
    def i64(self,v): self.buf+=struct.pack("<q",v)
    def u16(self,v): self.buf+=struct.pack("<H",v)
    def f32(self,v): self.buf+=struct.pack("<f",v)
    def u8(self,v): self.buf.append(v&0xFF)
    def fstring(self,s):
        if s=="": self.i32(0); return
        try:
            b=s.encode("latin1")+b"\x00"; self.i32(len(b)); self.bytes(b)
        except UnicodeEncodeError:
            b=s.encode("utf-16-le")+b"\x00\x00"; self.i32(-(len(b)//2)); self.bytes(b)

def read_header(r):
    if r.bytes(4)!=b"GVAS": raise GvasError("bad magic")
    h={"magic":b"GVAS"}
    h["save_game_version"]=r.i32(); h["package_version"]=r.i32()
    h["engine_major"]=r.u16(); h["engine_minor"]=r.u16(); h["engine_patch"]=r.u16()
    h["engine_build"]=r.u32(); h["engine_branch"]=r.fstring()
    h["custom_format_version"]=r.i32()
    cnt=r.i32(); cfs=[]
    for _ in range(cnt): cfs.append((r.bytes(16), r.i32()))
    h["custom_formats"]=cfs; h["save_game_class"]=r.fstring()
    return h

def write_header(w,h):
    w.bytes(h["magic"]); w.i32(h["save_game_version"]); w.i32(h["package_version"])
    w.u16(h["engine_major"]); w.u16(h["engine_minor"]); w.u16(h["engine_patch"])
    w.u32(h["engine_build"]); w.fstring(h["engine_branch"])
    w.i32(h["custom_format_version"]); w.i32(len(h["custom_formats"]))
    for guid,ver in h["custom_formats"]: w.bytes(guid); w.i32(ver)
    w.fstring(h["save_game_class"])

def read_properties(r):
    props=[]
    while True:
        name=r.fstring()
        if name=="None" or name=="": break
        props.append(read_property(r,name))
    return props

def read_property(r,name):
    ptype=r.fstring(); size=r.i32(); array_index=r.i32()
    prop={"name":name,"type":ptype,"array_index":array_index}
    if ptype=="BoolProperty":
        prop["value"]=r.u8()!=0; prop["_terminator"]=r.u8()
    elif ptype=="IntProperty":
        prop["_term"]=r.u8(); prop["value"]=r.i32()
    elif ptype=="Int64Property":
        prop["_term"]=r.u8(); prop["value"]=r.i64()
    elif ptype=="UInt32Property":
        prop["_term"]=r.u8(); prop["value"]=r.u32()
    elif ptype=="FloatProperty":
        prop["_term"]=r.u8(); prop["value"]=r.f32()
    elif ptype=="StrProperty":
        prop["_term"]=r.u8(); prop["value"]=r.fstring()
    elif ptype=="NameProperty":
        prop["_term"]=r.u8(); prop["value"]=r.fstring()
    elif ptype=="EnumProperty":
        prop["enum_type"]=r.fstring(); prop["_term"]=r.u8(); prop["value"]=r.fstring()
    elif ptype=="ByteProperty":
        prop["enum_type"]=r.fstring(); prop["_term"]=r.u8()
        prop["value"]= r.u8() if prop["enum_type"]=="None" else r.fstring()
    elif ptype=="StructProperty":
        prop["struct_type"]=r.fstring(); prop["guid"]=r.bytes(16); prop["_term"]=r.u8()
        prop["value"]=parse_struct_body(prop["struct_type"], r.bytes(size))
    elif ptype=="ArrayProperty":
        prop["inner_type"]=r.fstring(); prop["_term"]=r.u8()
        prop["value"]=parse_array_body(prop["inner_type"], r.bytes(size))
    elif ptype=="SetProperty":
        prop["inner_type"]=r.fstring(); prop["_term"]=r.u8()
        prop["value"]=parse_set_body(prop["inner_type"], r.bytes(size))
    elif ptype=="MapProperty":
        prop["key_type"]=r.fstring(); prop["val_type"]=r.fstring(); prop["_term"]=r.u8()
        prop["value"]=parse_map_body(prop["key_type"],prop["val_type"], r.bytes(size))
    else:
        prop["_raw"]=r.bytes(size); prop["value"]=None
    return prop

def parse_struct_body(st,body):
    if st in BINARY_STRUCT_TYPES: return {"_binary":True,"raw":body}
    rr=Reader(body); props=read_properties(rr); trailing=rr.bytes(rr.remaining())
    return {"_binary":False,"props":props,"_trailing":trailing}

def parse_array_body(inner,body):
    rr=Reader(body); count=rr.i32()
    if inner=="StructProperty":
        fn=rr.fstring(); ft=rr.fstring(); isz=rr.i32(); iix=rr.i32()
        st=rr.fstring(); guid=rr.bytes(16); term=rr.u8()
        elems=[read_properties(rr) for _ in range(count)]
        trailing=rr.bytes(rr.remaining())
        return {"kind":"struct","count":count,"field_name":fn,"field_type":ft,
                "inner_index":iix,"struct_type":st,"guid":guid,"_term":term,
                "elements":elems,"_trailing":trailing}
    else:
        return {"kind":"scalar","count":count,"elements":[read_scalar(rr,inner) for _ in range(count)]}

def parse_set_body(inner,body):
    rr=Reader(body); nr=rr.i32(); count=rr.i32()
    return {"num_removed":nr,"count":count,"elements":[read_scalar(rr,inner) for _ in range(count)]}

def parse_map_body(kt,vt,body):
    rr=Reader(body); nr=rr.i32(); count=rr.i32(); pairs=[]
    for _ in range(count):
        k=read_map_side(rr,kt); v=read_map_side(rr,vt)
        pairs.append([k,v])
    return {"num_removed":nr,"count":count,"pairs":pairs,
            "key_type":kt,"val_type":vt}

def read_map_side(rr,t):
    """One key/value in a MapProperty. Scalars stored bare; StructProperty
    values are an inline property list terminated by 'None' (no header/guid)."""
    if t=="StructProperty":
        return {"_map_struct":True,"props":read_properties(rr)}
    return read_scalar(rr,t)

def read_scalar(rr,t):
    if t=="IntProperty": return rr.i32()
    if t=="Int64Property": return rr.i64()
    if t=="FloatProperty": return rr.f32()
    if t=="BoolProperty": return rr.u8()!=0
    if t in ("NameProperty","StrProperty","EnumProperty"): return rr.fstring()
    if t=="ByteProperty": return rr.u8()
    raise GvasError(f"unsupported scalar type in container: {t}")

def write_properties(w,props):
    for p in props: write_property(w,p)
    w.fstring("None")

def write_property(w,prop):
    t=prop["type"]; w.fstring(prop["name"]); w.fstring(t)
    sp=len(w.buf); w.i32(0); w.i32(prop.get("array_index",0))
    if t=="BoolProperty":
        w.u8(1 if prop["value"] else 0); w.u8(prop.get("_terminator",0)); _ps(w,sp,0)
    elif t=="IntProperty":
        w.u8(prop.get("_term",0)); s=len(w.buf); w.i32(prop["value"]); _ps(w,sp,len(w.buf)-s)
    elif t=="Int64Property":
        w.u8(prop.get("_term",0)); s=len(w.buf); w.i64(prop["value"]); _ps(w,sp,len(w.buf)-s)
    elif t=="UInt32Property":
        w.u8(prop.get("_term",0)); s=len(w.buf); w.u32(prop["value"]); _ps(w,sp,len(w.buf)-s)
    elif t=="FloatProperty":
        w.u8(prop.get("_term",0)); s=len(w.buf); w.f32(prop["value"]); _ps(w,sp,len(w.buf)-s)
    elif t=="StrProperty":
        w.u8(prop.get("_term",0)); s=len(w.buf); w.fstring(prop["value"]); _ps(w,sp,len(w.buf)-s)
    elif t=="NameProperty":
        w.u8(prop.get("_term",0)); s=len(w.buf); w.fstring(prop["value"]); _ps(w,sp,len(w.buf)-s)
    elif t=="EnumProperty":
        w.fstring(prop["enum_type"]); w.u8(prop.get("_term",0)); s=len(w.buf); w.fstring(prop["value"]); _ps(w,sp,len(w.buf)-s)
    elif t=="ByteProperty":
        w.fstring(prop["enum_type"]); w.u8(prop.get("_term",0)); s=len(w.buf)
        if prop["enum_type"]=="None": w.u8(prop["value"])
        else: w.fstring(prop["value"])
        _ps(w,sp,len(w.buf)-s)
    elif t=="StructProperty":
        w.fstring(prop["struct_type"]); w.bytes(prop["guid"]); w.u8(prop.get("_term",0))
        s=len(w.buf); _wsb(w,prop["struct_type"],prop["value"]); _ps(w,sp,len(w.buf)-s)
    elif t=="ArrayProperty":
        w.fstring(prop["inner_type"]); w.u8(prop.get("_term",0))
        s=len(w.buf); _wab(w,prop["inner_type"],prop["value"]); _ps(w,sp,len(w.buf)-s)
    elif t=="SetProperty":
        w.fstring(prop["inner_type"]); w.u8(prop.get("_term",0))
        s=len(w.buf); _wsetb(w,prop["inner_type"],prop["value"]); _ps(w,sp,len(w.buf)-s)
    elif t=="MapProperty":
        w.fstring(prop["key_type"]); w.fstring(prop["val_type"]); w.u8(prop.get("_term",0))
        s=len(w.buf); _wmb(w,prop["key_type"],prop["val_type"],prop["value"]); _ps(w,sp,len(w.buf)-s)
    else:
        s=len(w.buf); w.bytes(prop.get("_raw",b"")); _ps(w,sp,len(w.buf)-s)

def _ps(w,sp,size): struct.pack_into("<i",w.buf,sp,size)

def _wsb(w,st,v):
    if v.get("_binary"): w.bytes(v["raw"])
    else: write_properties(w,v["props"]); w.bytes(v.get("_trailing",b""))

def _wab(w,inner,v):
    w.i32(v["count"])
    if v["kind"]=="struct":
        w.fstring(v["field_name"]); w.fstring(v["field_type"])
        isp=len(w.buf); w.i32(0); w.i32(v.get("inner_index",0))
        w.fstring(v["struct_type"]); w.bytes(v["guid"]); w.u8(v.get("_term",0))
        ist=len(w.buf)
        for e in v["elements"]: write_properties(w,e)
        w.bytes(v.get("_trailing",b""))
        struct.pack_into("<i",w.buf,isp,len(w.buf)-ist)
    else:
        for e in v["elements"]: write_scalar(w,inner,e)

def _wsetb(w,inner,v):
    w.i32(v.get("num_removed",0)); w.i32(v["count"])
    for e in v["elements"]: write_scalar(w,inner,e)

def _wmb(w,kt,vt,v):
    w.i32(v.get("num_removed",0)); w.i32(v["count"])
    for k,val in v["pairs"]:
        write_map_side(w,kt,k); write_map_side(w,vt,val)

def write_map_side(w,t,v):
    if t=="StructProperty": write_properties(w,v["props"])
    else: write_scalar(w,t,v)

def write_scalar(w,t,v):
    if t=="IntProperty": w.i32(v)
    elif t=="Int64Property": w.i64(v)
    elif t=="FloatProperty": w.f32(v)
    elif t=="BoolProperty": w.u8(1 if v else 0)
    elif t in ("NameProperty","StrProperty","EnumProperty"): w.fstring(v)
    elif t=="ByteProperty": w.u8(v)
    else: raise GvasError(f"unsupported scalar type in container: {t}")

class SaveFile:
    def __init__(self,header,properties,trailer):
        self.header=header; self.properties=properties; self.trailer=trailer
    @classmethod
    def load(cls,path):
        with open(path,"rb") as f: return cls.from_bytes(f.read())
    @classmethod
    def from_bytes(cls,data):
        r=Reader(data); h=read_header(r); props=read_properties(r); tr=r.bytes(r.remaining())
        return cls(h,props,tr)
    def to_bytes(self):
        w=Writer(); write_header(w,self.header); write_properties(w,self.properties); w.bytes(self.trailer)
        return bytes(w.buf)
    def save(self,path):
        with open(path,"wb") as f: f.write(self.to_bytes())

if __name__=="__main__":
    import sys
    sf=SaveFile.load(sys.argv[1]); out=sf.to_bytes(); orig=open(sys.argv[1],"rb").read()
    print("round-trip identical:", out==orig, "len",len(orig),"->",len(out))
