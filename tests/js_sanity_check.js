const fs = require('fs');
const { execSync } = require('child_process');

const filesToCheck = [
    'player/player_v2.js',
    'player/player_v2_functions_to_add.js'
];

console.log('🔍 Running Syntax Sanity Check...');

let hasErrors = false;

filesToCheck.forEach(file => {
    try {
        if (fs.existsSync(file)) {
            execSync(`node --check "${file}"`, { stdio: 'pipe' });
            console.log(`✅ ${file} passed syntax check.`);
        } else {
            console.warn(`⚠️  ${file} not found, skipping.`);
        }
    } catch (error) {
        console.error(`❌ Syntax Error in ${file}:`);
        console.error(error.stderr.toString());
        hasErrors = true;
    }
});

if (hasErrors) {
    console.error('💥 Sanity Check Failed! Fix syntax errors before committing.');
    process.exit(1);
} else {
    console.log('✨ All files passed syntax check.');
    process.exit(0);
}
