import re
import json
import os
import glob
from typing import List, Dict, Set
from collections import defaultdict


class APIParameterExtractor:
    def __init__(self):
        self.params = []
    
    def extract_api_parameters(self, js_code: str) -> List[Dict]:
        if not js_code:
            raise ValueError('无法获取页面内容')
        
        print('开始精准提取API参数...')
        
        self.params = []
        
        extract_object_property_names(js_code, self.params)
        extract_destructuring_variables(js_code, self.params)
        extract_nested_destructuring(js_code, self.params)
        extract_function_parameters(js_code, self.params)
        extract_variable_assignments(js_code, self.params)
        extract_api_request_params(js_code, self.params)
        extract_url_params(js_code, self.params)
        extract_config_objects(js_code, self.params)
        extract_route_params(js_code, self.params)
        
        
        classified_params = classify_parameters(self.params)
        
        return remove_duplicates(classified_params)


def extract_object_property_names(js_code: str, params: List[Dict]):
    print('开始提取对象属性...')
    
    object_patterns = [
        r'(?:^|,|\n|\r\n)\s*([a-zA-Z_$][a-zA-Z0-9_$]*)\s*:',
        r'{[\s]*["\']([a-zA-Z_$][a-zA-Z0-9_$]*)["\'][\s]*:',
        r"{[\s]*'([a-zA-Z_$][a-zA-Z0-9_$]*)'[\s]*:"
    ]
    
    for pattern in object_patterns:
        matches = re.finditer(pattern, js_code)
        for match in matches:
            param_name = match.group(1)
            if is_valid_parameter_name(param_name):
                params.append({
                    'value': param_name,
                    'source': 'object_property'
                })


def extract_destructuring_variables(js_code: str, params: List[Dict]):
    print('开始提取解构变量...')
    
    destructuring_pattern = r'(?:const|let|var)\s*\{([^}]+)\}\s*='
    matches = re.finditer(destructuring_pattern, js_code)
    
    for match in matches:
        inner_content = match.group(1)
        print(f'解构内容: {inner_content}')
        
        variable_pattern = r'([a-zA-Z_$][a-zA-Z0-9_$]*)(?:\s*:\s*([a-zA-Z_$][a-zA-Z0-9_$]*))?'
        var_matches = re.finditer(variable_pattern, inner_content)
        
        for var_match in var_matches:
            variable_name = var_match.group(2) or var_match.group(1)
            
            if variable_name and is_valid_parameter_name(variable_name):
                params.append({
                    'value': variable_name,
                    'source': 'destructuring'
                })
                print(f'✅ 添加解构变量: {variable_name}')


def extract_nested_destructuring(js_code: str, params: List[Dict]):
    print('开始提取嵌套解构...')
    
    nested_patterns = [
        r'(?:const|let|var)\s*\{[^}]*:\s*\{([^}]+)\}[^}]*\}',
        r'(?:const|let|var)\s*\{[^}]*:\s*\{([^}]+)\}[^}]*,[^}]*:\s*\{([^}]+)\}[^}]*\}'
    ]
    
    for index, pattern in enumerate(nested_patterns):
        print(f'使用嵌套模式 {index} 匹配: {pattern}')
        matches = re.finditer(pattern, js_code)
        
        for match in matches:
            print(f'找到嵌套解构: {match.group(0)}')
            
            for i in range(1, len(match.groups()) + 1):
                if match.group(i):
                    inner_content = match.group(i)
                    print(f'嵌套块 {i} 内容: {inner_content}')
                    
                    inner_vars = [v.strip() for v in inner_content.split(',')]
                    inner_vars = [v for v in inner_vars if v and is_valid_parameter_name(v)]
                    
                    for var_name in inner_vars:
                        params.append({
                            'value': var_name,
                            'source': 'nested_destructuring'
                        })
                        print(f'✅ 添加嵌套解构变量: {var_name}')
    
    specific_pattern = r'const\s*\{\s*settings:\s*\{([^}]+)\}\s*,\s*preferences:\s*\{([^}]+)\}\s*\}\s*=\s*userConfig'
    specific_match = re.search(specific_pattern, js_code)
    if specific_match:
        print(f'找到特定嵌套模式: {specific_match.group(0)}')
        
        settings_vars = [v.strip() for v in specific_match.group(1).split(',')]
        settings_vars = [v for v in settings_vars if v and is_valid_parameter_name(v)]
        
        preferences_vars = [v.strip() for v in specific_match.group(2).split(',')]
        preferences_vars = [v for v in preferences_vars if v and is_valid_parameter_name(v)]
        
        for var_name in settings_vars + preferences_vars:
            params.append({
                'value': var_name,
                'source': 'nested_destructuring'
            })


def extract_function_parameters(js_code: str, params: List[Dict]):
    function_patterns = [
        r'function\s+[^(]*\(\s*([^)]+)\s*\)',
        r'\(\s*([^)]+)\s*\)\s*=>',
        r'function\s+[^(]*\(\s*\{([^}]+)}\s*\)',
        r'\(\s*\{([^}]+)}\s*\)\s*=>'
    ]
    
    for pattern in function_patterns:
        matches = re.finditer(pattern, js_code)
        for match in matches:
            params_str = match.group(1)
            param_names = [p.strip() for p in params_str.split(',')]
            param_names = [p for p in param_names if p and p != '{' and p != '}']
            
            processed_names = []
            for p in param_names:
                if '{' in p:
                    p = p.replace('{', '').replace('}', '').strip()
                if '=' in p:
                    p = p.split('=')[0].strip()
                if p:
                    processed_names.append(p)
            
            for param_name in processed_names:
                if is_valid_parameter_name(param_name):
                    params.append({
                        'value': param_name,
                        'source': 'function_param'
                    })


def extract_variable_assignments(js_code: str, params: List[Dict]):
    assignment_patterns = [
        r'(?:const|let|var)\s+([a-zA-Z_$][a-zA-Z0-9_$]*)\s*=',
        r'([a-zA-Z_$][a-zA-Z0-9_$]*)\s*=\s*[^{]'
    ]
    
    for pattern in assignment_patterns:
        matches = re.finditer(pattern, js_code)
        for match in matches:
            param_name = match.group(1)
            if is_valid_parameter_name(param_name) and not is_common_variable(param_name):
                params.append({
                    'value': param_name,
                    'source': 'variable_assignment'
                })


def extract_api_request_params(js_code: str, params: List[Dict]):
    api_patterns = [
        r'(?:fetch|axios|\.(?:get|post|put|delete|patch))\([^,]+,\s*\{([^}]*)}',
        r'\.(?:then|catch)\([^,]*\{([^}]*)}',
        r'\([^)]*\{([^}]*)}[^)]*\)'
    ]
    
    for pattern in api_patterns:
        matches = re.finditer(pattern, js_code)
        for match in matches:
            object_content = match.group(1)
            prop_regex = r'(["\']?)([a-zA-Z_$][a-zA-Z0-9_$]*)\1\s*:'
            prop_matches = re.finditer(prop_regex, object_content)
            
            for prop_match in prop_matches:
                prop_name = prop_match.group(2)
                if is_valid_parameter_name(prop_name):
                    params.append({
                        'value': prop_name,
                        'source': 'api_request'
                    })


def extract_url_params(js_code: str, params: List[Dict]):
    url_patterns = [
        r'[?&]([a-zA-Z_$][a-zA-Z0-9_$]*)=',
        r'\.(?:set|append)\(["\']([^"\']+)["\']',
        r'[?&]\$\{([^}]+)\}'
    ]
    
    for pattern in url_patterns:
        matches = re.finditer(pattern, js_code)
        for match in matches:
            param_name = match.group(1)
            if is_valid_parameter_name(param_name):
                params.append({
                    'value': param_name,
                    'source': 'url_param'
                })


def extract_config_objects(js_code: str, params: List[Dict]):
    config_patterns = [
        r'(?:config|options|params|settings)\s*=\s*\{([^}]*)}',
        r'(?:headers|data|body|query)\s*:\s*\{([^}]*)}'
    ]
    
    for pattern in config_patterns:
        matches = re.finditer(pattern, js_code)
        for match in matches:
            config_content = match.group(1)
            prop_regex = r'(["\']?)([a-zA-Z_$][a-zA-Z0-9_$]*)\1\s*:'
            prop_matches = re.finditer(prop_regex, config_content)
            
            for prop_match in prop_matches:
                prop_name = prop_match.group(2)
                if is_valid_parameter_name(prop_name):
                    params.append({
                        'value': prop_name,
                        'source': 'config_object'
                    })


def extract_route_params(js_code: str, params: List[Dict]):
    route_patterns = [
        r'/:(?::)?([a-zA-Z_$][a-zA-Z0-9_$]*)',
        r'path:.*?/:(?::)?([a-zA-Z_$][a-zA-Z0-9_$]*)',
        r'/\{([a-zA-Z_$][a-zA-Z0-9_$]*)\}',
        r'/\[([a-zA-Z_$][a-zA-Z0-9_$]*)\]',
        r'["\'`](/:[^/"\'`]*?/([a-zA-Z_$][a-zA-Z0-9_$]*))["\'`]'
    ]
    
    for pattern in route_patterns:
        matches = re.finditer(pattern, js_code)
        for match in matches:
            param_name = match.group(1)
            if is_valid_parameter_name(param_name):
                params.append({
                    'value': param_name,
                    'source': 'route_param'
                })
    
    extract_route_params_from_urls(js_code, params)


def extract_route_params_from_urls(js_code: str, params: List[Dict]):
    url_patterns = [
        r'["\'`](/api/[^"\'`]*?/(?::|\{|\[)([a-zA-Z_$][a-zA-Z0-9_$]*)(?::|\}|\]))[^"\'`]*?["\'`]',
        r'["\'`](/v\d+/[\w/]*?/(?::|\{|\[)([a-zA-Z_$][a-zA-Z0-9_$]*)(?::|\}|\]))[^"\'`]*?["\'`]'
    ]
    
    for pattern in url_patterns:
        matches = re.finditer(pattern, js_code)
        for match in matches:
            param_name = match.group(2)
            if is_valid_parameter_name(param_name):
                params.append({
                    'value': param_name,
                    'source': 'route_param'
                })


def classify_parameters(params: List[Dict]) -> List[Dict]:
    classified = []
    
    for param in params:
        category = 'general'
        priority = 1
        tags = []
        
        name = param['value'].lower()
        
        if param['source'] == 'route_param':
            priority = 4
            tags.append('route')
        
        if 'id' in name or name.endswith('id'):
            category = 'identifier'
            priority = 4
            tags.append('id')
        
        if any(keyword in name for keyword in ['token', 'auth', 'key', 'secret', 'password', 'session']):
            category = 'authentication'
            priority = 5
            tags.append('auth')
        
        if any(keyword in name for keyword in ['page', 'size', 'limit', 'offset']):
            category = 'pagination'
            priority = 2
            tags.append('pagination')
        
        if any(keyword in name for keyword in ['time', 'date', 'timestamp']):
            category = 'timestamp'
            priority = 3
            tags.append('time')
        
        if any(keyword in name for keyword in ['status', 'state']):
            category = 'status'
            priority = 3
            tags.append('status')
        
        if 'url' in param['source'] or 'api' in param['source']:
            priority = min(5, priority + 1)
            tags.append('api')
        
        classified.append({
            **param,
            'category': category,
            'priority': priority,
            'tags': list(set(tags))
        })
    
    return sorted(classified, key=lambda x: x['priority'], reverse=True)


def is_valid_parameter_name(name: str) -> bool:
    if not name or not isinstance(name, str):
        return False
    
    if len(name) < 2 or len(name) > 50:
        return False
    
    if not re.match(r'^[a-zA-Z_$][a-zA-Z0-9_$]*$', name):
        return False
    
    if '_' in name:
        return False
    
    keywords = [
        'var', 'let', 'const', 'function', 'if', 'else', 'for', 'while', 'return',
        'class', 'import', 'export', 'default', 'extends', 'super', 'this', 'new',
        'typeof', 'instanceof', 'void', 'delete', 'in', 'of', 'try', 'catch', 'finally',
        'throw', 'debugger', 'with', 'yield', 'await', 'async', 'static', 'set',
        'true', 'false', 'null', 'undefined'
    ]
    
    if name in keywords:
        return False
    
    excluded_names = [
        'headers', 'response', 'request', 'error', 'success',
        'then', 'catch', 'finally', 'resolve', 'reject', 'promise',
        'fn', 'func', 'obj', 'arr', 'str', 'bool', 'date', 'reg', 'regex',
        'i', 'j', 'k', 'x', 'y', 'z', 'n', 'm', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h',
        'props', 'state', 'ref', 'children', 'style'
    ]
    
    if name in excluded_names:
        return False
    
    return True


def is_common_variable(name: str) -> bool:
    common_vars = [
        'e', 't', 'a', 'n', 'l', 'r', 'i', 'o', 'c', 'u', 's', 'd', 'm', 'v', 'p', 'h',
        'f', 'g', 'b', 'y', 'N', 'I', 'w', 'E', 'k', 'O', 'x', 'j', 'S', 'C', 'A', '_'
    ]
    
    return name in common_vars or len(name) == 1


def remove_duplicates(params: List[Dict]) -> List[Dict]:
    seen = set()
    unique_params = []
    
    for param in params:
        if param['value'] not in seen:
            seen.add(param['value'])
            unique_params.append(param)
    
    return sorted(unique_params, key=lambda x: x['value'])


def extract_from_file(file_path: str) -> List[Dict]:
    with open(file_path, 'r', encoding='utf-8') as f:
        js_code = f.read()
    
    extractor = APIParameterExtractor()
    return extractor.extract_api_parameters(js_code)


def extract_from_code(js_code: str) -> List[Dict]:
    extractor = APIParameterExtractor()
    return extractor.extract_api_parameters(js_code)


def save_results_by_category(params: List[Dict], output_dir: str = 'results'):
    os.makedirs(output_dir, exist_ok=True)
    
    category_groups = defaultdict(list)
    for param in params:
        category_groups[param['category']].append(param)
    
    for category, items in category_groups.items():
        output_file = os.path.join(output_dir, f'{category}.txt')
        with open(output_file, 'w', encoding='utf-8') as f:
            for item in items:
                f.write(f"{item['value']}\n")
        print(f'✅ 已保存 {category} 分类到 {output_file} ({len(items)} 个参数)')
    
    return category_groups


def save_all_results(params: List[Dict], output_file: str = 'results/all_results_all.txt'):
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        for param in params:
            f.write(f"{param['value']}\n")
    
    print(f'✅ 已保存总表到 {output_file} ({len(params)} 个参数)')


def extract_from_directory(directory: str) -> List[Dict]:
    all_params = []
    
    js_files = glob.glob(os.path.join(directory, '*.js'))
    
    if not js_files:
        print(f'❌ 在目录 {directory} 中未找到 .js 文件')
        return all_params
    
    print(f'📁 在目录 {directory} 中找到 {len(js_files)} 个 JS 文件')
    
    for js_file in js_files:
        print(f'\n处理文件: {os.path.basename(js_file)}')
        try:
            params = extract_from_file(js_file)
            all_params.extend(params)
            print(f'✅ 从 {os.path.basename(js_file)} 提取到 {len(params)} 个参数')
        except Exception as e:
            print(f'❌ 处理 {os.path.basename(js_file)} 时出错: {e}')
    
    return remove_duplicates(all_params)


if __name__ == '__main__':
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description='从 JavaScript 文件中提取 API 参数')
    parser.add_argument('path', help='JavaScript 文件路径或包含 JS 文件的目录路径')
    parser.add_argument('--output-dir', default='results', help='输出目录 (默认: results)')
    parser.add_argument('--no-save', action='store_true', help='不保存到文件，只打印结果')
    
    args = parser.parse_args()
    
    if os.path.isdir(args.path):
        print(f'📂 从目录提取: {args.path}')
        result = extract_from_directory(args.path)
    elif os.path.isfile(args.path):
        print(f'📄 从文件提取: {args.path}')
        result = extract_from_file(args.path)
    else:
        print(f'❌ 路径不存在: {args.path}')
        sys.exit(1)
    
    print('\n' + '='*50)
    print('提取结果汇总:')
    print('='*50)
    print(f'总共提取到 {len(result)} 个唯一参数')
    
    category_count = defaultdict(int)
    for param in result:
        category_count[param['category']] += 1
    
    print('\n分类统计:')
    for category, count in sorted(category_count.items()):
        print(f'  {category}: {count} 个参数')
    
    if not args.no_save:
        print('\n' + '='*50)
        print('保存结果...')
        print('='*50)
        save_results_by_category(result, args.output_dir)
        save_all_results(result, os.path.join(args.output_dir, 'all_results_all.txt'))
        print(f'\n✅ 所有结果已保存到目录: {args.output_dir}')
    else:
        print('\n' + '='*50)
        print('详细结果:')
        print('='*50)
        print(json.dumps(result, indent=2, ensure_ascii=False))
