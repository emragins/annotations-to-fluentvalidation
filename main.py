import sys
import os
import mmap
import re 

_debug = False

excludeTagsFromDeletion = ['DataType', 'Password', 'EmailAddress']

class FileLocator: 
    def __init__(self):
        self.excludeDirs = set(["node_modules", "packages", "bower_components", "bin", "obj"])
        self.includeFiles = set([".cs"])
        self.excludeFiles = set(["dbEntity", "DbContext"])

    def decideFile(self, path, file):
        fullPath = os.path.join(path, file)
        if(os.path.splitext(fullPath)[1] in self.includeFiles):
            for e in self.excludeFiles:
                if(file.find(e) != -1):
                    return False
            f = open(fullPath)
            s = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
            if s.find(b'DataAnnotations') != -1:
                s.close()
                return True
        return False

    def getFiles(self, mypath):
        f = []
        for (cur_path, dirs, filenames) in os.walk(mypath):
            dirs[:] = [d for d in dirs if d not in self.excludeDirs]
            for file in [f for f in filenames if self.decideFile(cur_path, f)]:
                full = os.path.join(cur_path, file)
                f.append(full)
            
        return f



class Property:
    name = None
    typ = None
    error = None
    
    def __init__(self, name, typ):
        self.name = name
        self.typ = typ

    def __str__(self):
        # if self.error:
        #     return "Annotation-Error: " + str(self.label) + ", Error: " + str(self.error)
            
        return "Property: " + str(self.name)  +  " (" +  str(self.typ) +  ")"
               

class Annotation:
    label = None
    message = None
    values = None
    error = None
    
    def __init__(self):
        pass

    def __str__(self):
        if self.error:
            return "Annotation-Error: " + str(self.label) + ", Error: " + str(self.error)
            
        return "Annotation: " + str(self.label) + ", Values: " + str(self.values) + ", Message: " + str(self.message)
      

class LineParser:
        
    validName = r'([a-zA-Z1-9_]+)'
    validType = validName + r'(<.*>)?' + r'(\[\])?' + r'(\?)?'
    excludeAnnotations = set(["Display", "AdditionalMetadata", "NotMapped", "AuthorizePermissions", "ForeignKey"])

        
    def findClassName(line):
        r = r'.*(\s+class\s+)'+LineParser.validName
        m = re.match(r, line)
        if m:
            name = m.group(2)
            if(_debug):
                print("Found class", name)
            return name
            
    def findProperty(line):
        r = r'(.*public (virtual)?\s?)' + LineParser.validType + '\s'  + LineParser.validName
        m = re.match(r, line)
        if m:
            t = m.group(3)
            if m.group(4):
                t += m.group(4)
            if m.group(5):
                t += m.group(5)
                
            p = m.group(7)
            
            prop = Property(p,t)
            return prop
            
            
    def findAnnotation(line):
        r_onLine = r'\s*\[.*\]'
        r_message = r'.*ErrorMessage = "(.*\))'
    
        if(not re.match(r_onLine, line)):
            return
            
        for exclude in LineParser.excludeAnnotations:
            if(re.search(r'\[' + exclude, line)):
                return
                
        a = Annotation() 
        
        if(_debug):
            print("Annotation on line", line)
        
        r_inside = r'(\s*\[)([a-zA-Z]+)(\((.*)\))?\]'
        m_annotation = re.match(r_inside, line)
        a.label = m_annotation.group(2)
        
        params = m_annotation.group(3)
        if(params):
            params = params[1:-1]
            
            if(_debug):
                print("Params: " , params)
        
        m_message = re.match(r_message, line)
        if m_message: 
            a.message = m_message.group(1)[:-2]

        if(a.label in ['MinLength', 'MaxLength', 'StringLength']):
            r_v = r"(\d+|Int32.MaxValue)"
            m_v = re.match(r_v, params)
            if not m_v:
                a.error = params
                return a
            a.values = m_v.group(1)           
        elif(a.label in ['Range']):
            r_v = r".*(\d+)(, )(\d+|(int|Int32).MaxValue)"
            m_v = re.match(r_v, params)
            if not m_v:
                a.error = line
                return a 
            a.values = m_v.group(1), m_v.group(3)
        elif(a.label in ['DataType']):
            a.values = params
        if(re.search(r"\[StringLength", line)):
            a.label = 'StringLength'
        
        return a
        

class Action:
    def __init__(self, action, lineNumber, lines):
        self.action = action
        self.lineNumber = lineNumber
        self.lines = lines        
        
    def __str__(self):
        return "Action: " + str(self.action) + " at " + str(self.lineNumber) + "\n".join(self.lines)
 
class Builder:
    lines = []
    
    def __init__(self, className, validations):
        self.className = className
        self.validations = validations
        self.lines = []
        self.indent = "    "         
    
    def addLine(self, text):
        self.lines.append(self.indent + text)
    def pushIndent(self):
        self.indent += "    "
    def popIndent(self):
        self.indent = self.indent[:-4]
        
    def build(self):
        newClass = self.className + "Validator"
        self.addLine("public class " + newClass + " : AbstractValidator<" + self.className + ">")
        self.startWrap()
        
        self.addLine("public " + newClass + "()")
        self.startWrap()

        for p, ans in self.validations:
            for a in self.merge(ans):
                self.addLine(self.createRule(p, a))

        self.closeWrap()
        
        
        self.closeWrap()
        self.addLine("")
        
        return self.lines.copy()            
        
    def startWrap(self):
        self.addLine("{")
        self.pushIndent()
        
    def closeWrap(self):
        self.popIndent()
        self.addLine("}")
        
    def merge(self, ans):
        # bs = [for a in ans if a.label in ['MinLength', 'MaxLength'])]
        # if(len(bs) < 2):
        #     return ans
        # 
        # ret = ans.copy()
        # for b in bs:
        #     ret.remove(b)
        # 
        # b = Annotation()
        # b.label = 'StringLength'
        # b.values = min(b.values for b in bs), max(b.values for b in bs)
        #     
        # bs.append(b)
        # return ret
        return ans
                
    def createRule(self, p, a):
        rule =  "RuleFor(x => x." + p.name + ")"

        if(a.label == 'Required'):
            rule += ".NotEmpty()"
        elif(a.label in ['MinLength', 'StringLength']):
            rule += ".Length(" + (a.values or "0") + ", Int32.MaxValue)"  
        elif(a.label in ['MaxLength']):
            rule += ".Length(0, " + a.values + ")"  
        elif(a.label in ['Range']):
            first = second = "0"
            if(a.values):
                first = a.values[0]
                second = a.values[1]
            rule += ".Length(" +first + ", " + second + ")"
        else:
           rule += ".UnresolvedTag(" +  str(a) + ")"
        
        if(a.message):
            rule += ".WithMessage(\"" + a.message + "\")"
            
        if(a.error):
            rule += ".Error(\"" + a.error + "\")"
            
        rule += ";"
        
        return rule
     
def convertToActions(cur_class, validations, i):
    actions = []
    for p, ans in validations:
        for a in ans:
            if  a.label not in excludeTagsFromDeletion:
                actions.append(Action("delete", a.lineNumber, []))
    
    newLines = Builder(cur_class, validations).build()
    actions.append(Action("insert", i, newLines))
    #print("\tValidations: ", validations)
    
    if(_debug):
        for a in actions:
            print("Action: ", a)
            
    return actions
            
def processFile(fullPath):
    print("Processing file", fullPath);

    f = open(fullPath, "r")
    lines = f.readlines()
    f.close()
    
    cur_class = None
    annotations = []
    validations = [] # property / annotation combination
    actions = []
    i = -1
    
    output = lines.copy()
    
    for line in lines:
        i += 1
        
        c = LineParser.findClassName(line)
        if c:
            
            if(validations):
                actions.extend(convertToActions(cur_class, validations, i))
                validations.clear()
            
            cur_class = c    
            continue
        
        a = LineParser.findAnnotation(line)
        if(a):
            a.lineNumber = i
            #print("Adding annotation", a)
            annotations.append(a)
           
            
        p = LineParser.findProperty(line)
        if(p):
            if(_debug):
                print("Found property",  p)
            if(annotations):
                #print("Appending to validations", p, annotations)
                validations.append((p, annotations.copy()))
                annotations.clear()
    
    # end read-text stage
    
    if(validations):
            actions.extend(convertToActions(cur_class, validations, i))
            validations.clear()     
            
    if actions:
        print ("Taking", len(actions), "actions")
        actions.sort( key= lambda x : x.lineNumber , reverse=True)
        # for a in actions:
        #     print("Sorted Actions: ", a)
         
        for a in actions:
            if(a.action == "delete"):
                del output[a.lineNumber]
            else:
                for line in reversed(a.lines):
                    output.insert(a.lineNumber, line + '\n')

        actions.clear()
        
        output.insert(0, 'using FluentValidation; \n')
        
        # for line in output:
        #     print(line)
        
        f = open(fullPath, "w")
        contents = "".join(output)
        f.write(contents)
        f.close()


directory_name = ''

try:
    directory_name=sys.argv[1]
    print(directory_name)
except:
    print('Please pass directory_name')
    sys.exit(1)
    

filesToTransform = FileLocator().getFiles(directory_name)


print("Files to transform")
print(filesToTransform)

print()

for file in filesToTransform:
    processFile(file)